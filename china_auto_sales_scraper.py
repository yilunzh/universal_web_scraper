import openai
import re, time, os
from firecrawl import FirecrawlApp
from dotenv import load_dotenv
import json
from tenacity import retry, wait_random_exponential, stop_after_attempt
from termcolor import colored
import tiktoken
from langsmith import traceable
from langsmith.wrappers import wrap_openai
import tempfile, requests
from openai import OpenAI

import instructor
from pydantic import BaseModel, Field, create_model
from typing import List, Optional, Dict, Any, Type, get_type_hints, Union

import pdb

# Load environment variables
load_dotenv()

# Initialize OpenAI client with LangSmith wrapper and instructor
client = wrap_openai(openai.Client())
instructor_client = instructor.from_openai(client, mode=instructor.Mode.TOOLS)

# Constants
GPT_MODEL = "gpt-4o"
max_token = 100000
llama_api_key = os.getenv("LLAMA_API_KEY")

def filter_empty_fields(model_instance: BaseModel) -> dict:
    """
    Recursively filter out empty fields from a Pydantic model instance.

    Args:
    model_instance (BaseModel): The Pydantic model instance to filter.

    Returns:
    dict: A dictionary with non-empty fields and their types.
    """
    def _filter(data: Any, field_type: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: _filter(v, field_type.get(k, type(v)) if isinstance(field_type, dict) else type(v))
                for k, v in data.items()
                if v not in [None, "", [], {}, "null", "None"]
            }
        elif isinstance(data, list):
            return [
                _filter(item, field_type.__args__[0] if hasattr(field_type, '__args__') else type(item))
                for item in data
                if item not in [None, "", [], {}, "null", "None"]
            ]
        else:
            return data

    data_dict = model_instance.dict(exclude_none=True)
    print(f"Data dict: {data_dict}")

    field_types = get_type_hints(model_instance.__class__)
    print(f"Field types: {field_types}")

    def get_inner_type(field_type):
        if hasattr(field_type, '__origin__') and field_type.__origin__ == list:
            return list
        return field_type

    filtered_dict = {
        k: {
            "value": _filter(v, get_inner_type(field_types.get(k, type(v)))),
            "type": str(get_inner_type(field_types.get(k, type(v))).__name__)
        }
        for k, v in data_dict.items()
        if v not in [None, "", [], {}, "null", "None"]
    }
    print(f"Filtered dict: {filtered_dict}")

    return filtered_dict
    # return filtered_dict

def create_filtered_model(data: List[Dict[str, Any]], base_model: Type[BaseModel], links_scraped: List[str]) -> Type[BaseModel]:
    """
    Create a filtered Pydantic model based on the provided data and base model.

    Args:
    data (List[Dict[str, Any]]): List of dictionaries containing field information.
    base_model (Type[BaseModel]): The base Pydantic model to extend from.
    links_scraped (List[str]): List of already scraped links.

    Returns:
    Type[BaseModel]: A new Pydantic model with filtered fields.
    """
    # Filter fields where value is None
    filtered_fields = {item['name']: item['value'] for item in data if item['value'] is None or isinstance(item['value'], list)}

    # Get fields with their annotations and descriptions
    fields_with_descriptions = {
        field: (base_model.__annotations__[field], Field(..., description=base_model.__fields__[field].description))
        for field in filtered_fields
    }

    # Constructing the desired JSON output
    data_to_collect = [
        {"name": field_name, "description": field_info.description}
        for field_name, (field_type, field_info) in fields_with_descriptions.items()
    ]

    print(f"Fields with descriptions: {data_to_collect}")
    # Create and return new Pydantic model
    FilteredModel = create_model('FilteredModel', **fields_with_descriptions)

    ExtendedDataPoints = create_model(
        'DataPoints',
        relevant_urls_might_contain_further_info=(List[str], Field([], description=f"{special_instruction} Relevant urls that we should scrape further that might contain information related to data points that we want to find; [DATA POINTS] {data_to_collect} [/END DATA POINTS] Prioritise urls on official their own domain first, even file url of image or pdf - those links can often contain useful information, we should always prioritise those urls instead of external ones; return None if cant find any; links cannot be any of the following: {links_scraped}")),
        __base__=FilteredModel
    )

    return ExtendedDataPoints


def extract_data_from_content(content, data_points, links_scraped, url):
    """
    Extract structured data from parsed content using the GPT model.

    Args:
    content (str): The parsed content to extract data from.
    data_points (List[Dict]): The list of data points to extract.
    links_scraped (List[str]): List of already scraped links.
    url (str): The URL of the content source.

    Returns:
    dict: The extracted structured data.
    """
    FilteredModel = create_filtered_model(data_points, DataPoints, links_scraped)

    # Extract structured data from natural language
    result = instructor_client.chat.completions.create(
        model=GPT_MODEL,
        response_model=FilteredModel,
        messages=[{"role": "user", "content": content}],
    )

    filtered_data = filter_empty_fields(result)

    data_to_update = [
        {"name": key, "value": value["value"], "reference": url, "type": value["type"]}
        for key, value in filtered_data.items() if key != 'relevant_urls_might_contain_further_info'
    ]

    update_data(data_points, data_to_update)

    return result.json()

def update_data(data_points, datas_update):
    """
    Update the state with new data points found.

    Args:
        data_points (list): The current data points state
        datas_update (List[dict]): The new data points found, have to follow the format [{"name": "xxx", "value": "xxx", "reference": "xxx"}]

    Returns:
        str: A message indicating the update status
    """
    print(f"Updating the data {datas_update}")

    try:
        for data in datas_update:
            for obj in data_points:
                if obj["name"] == data["name"]:
                    if data["type"].lower() == "dict":
                        obj["reference"] = data["reference"] if data["reference"] else "None"
                        obj["value"] = json.loads(data["value"])
                    elif data["type"].lower() == "str":
                        obj["reference"] = data["reference"]
                        obj["value"] = data["value"]
                    elif data["type"].lower() == "int":
                        obj["reference"] = data["reference"]
                        obj["value"] = data["value"]
                    elif data["type"].lower() == "list":
                        if isinstance(data["value"], str):
                            data_value = json.loads(data["value"])
                        else:
                            data_value = data["value"]

                        for item in data_value:
                            item["reference"] = data["reference"]

                        if obj["value"] is None:
                            obj["value"] = data_value
                        else:
                            obj["value"].extend(data_value)

        return "data updated"
    except Exception as e:
        print("Unable to update data points")
        print(f"Exception: {e}")
        return "Unable to update data points"

def extract_data_from_content(content, data_points, links_scraped, url):
    """
    Extract structured data from parsed content using the GPT model.

    Args:
    content (str): The parsed content to extract data from.
    data_points (List[Dict]): The list of data points to extract.
    links_scraped (List[str]): List of already scraped links.
    url (str): The URL of the content source.

    Returns:
    dict: The extracted structured data.
    """
    FilteredModel = create_filtered_model(data_points, DataPoints, links_scraped)

    # Extract structured data from natural language
    result = instructor_client.chat.completions.create(
        model=GPT_MODEL,
        response_model=FilteredModel,
        messages=[{"role": "user", "content": content}],
    )

    filtered_data = filter_empty_fields(result)

    data_to_update = [
        {"name": key, "value": value["value"], "reference": url, "type": value["type"]}
        for key, value in filtered_data.items() if key != 'relevant_urls_might_contain_further_info'
    ]

    update_data(data_points, data_to_update)

    return result.json()

@traceable(run_type="tool", name="Llama scraper")
def llama_parser(file_url, links_scraped):
    """
    Parse a file using the Llama API and extract structured data.

    Args:
    file_url (str): The URL of the file to parse.
    links_scraped (List[str]): List of already scraped links.

    Returns:
    dict: The extracted structured data or an error message.
    """
    try:
        job_id = create_parse_job(file_url)
        status = check_status(job_id)
        while status != "SUCCESS":
            status = check_status(job_id)
        markdown =  get_content(job_id)
        links_scraped.append(file_url)

        extracted_data = extract_data_from_content(markdown, data_points, links_scraped, file_url)

        return extracted_data

    except Exception as e:
        return f"Failed to parse the file: {e}"

# Web scraping function
@traceable(run_type="tool", name="Scrape")
def scrape(url, data_points, links_scraped):
    """
    Scrape a given URL and extract structured data.

    Args:
    url (str): The URL to scrape.
    data_points (List[Dict]): The list of data points to extract.
    links_scraped (List[str]): List of already scraped links.

    Returns:
    dict: The extracted structured data or an error message.
    """
    app = FirecrawlApp()

    try:
        scraped_data = app.scrape_url(url)
        markdown = scraped_data["markdown"][: (max_token * 2)]
        links_scraped.append(url)

        extracted_data = extract_data_from_content(markdown, data_points, links_scraped, url)

        return extracted_data
    except Exception as e:
        print("Unable to scrape the url")
        print(f"Exception: {e}")
        return "Unable to scrape the url"

@traceable(run_type="llm", name="Agent chat completion")
@retry(wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3))
def chat_completion_request(messages, tool_choice, tools, model=GPT_MODEL):
    """
    Make a chat completion request to the OpenAI API.

    Args:
        messages (List[Dict]): The conversation history.
        tool_choice (str): The chosen tool for the AI to use.
        tools (List[Dict]): Available tools for the AI to use.
        model (str): The GPT model to use.

    Returns:
        openai.ChatCompletion: The response from the OpenAI API.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
        )
        return response
    except Exception as e:
        print("Unable to generate ChatCompletion response")
        print(f"Exception: {e}")
        return e

@traceable(name="Optimise memory")
def memory_optimise(messages: list):
    """
    Optimize the conversation history to fit within token limits.

    Args:
        messages (List[Dict]): The full conversation history.

    Returns:
        List[Dict]: The optimized conversation history.
    """
    system_prompt = messages[0]["content"]

    # token count
    encoding = tiktoken.encoding_for_model(GPT_MODEL)

    if len(encoding.encode(str(messages))) > max_token:
        latest_messages = messages
        token_count_latest_messages = len(encoding.encode(str(latest_messages)))
        print(f"initial Token count of latest messages: {token_count_latest_messages}")

        while token_count_latest_messages > max_token:
            latest_messages.pop(0)
            token_count_latest_messages = len(encoding.encode(str(latest_messages)))
            print(f"Token count of latest messages: {token_count_latest_messages}")

        print(f"Final Token count of latest messages: {token_count_latest_messages}")

        index = messages.index(latest_messages[0])
        early_messages = messages[:index]

        prompt = f""" {early_messages}
        -----
        Above is the past history of conversation between user & AI, including actions AI already taken
        Please summarise the past actions taken so far, specifically around:
        - What data source have the AI look up already
        - What data points have been found so far

        SUMMARY:
        """

        response = client.chat.completions.create(
            model=GPT_MODEL, messages=[{"role": "user", "content": prompt}]
        )

        system_prompt = f"""{system_prompt}; Here is a summary of past actions taken so far: {response.choices[0].message.content}"""
        messages = [{"role": "system", "content": system_prompt}] + latest_messages

        return messages

    return messages

@traceable(name="Call agent")
def call_agent(
    prompt, system_prompt, tools, plan, data_points, entity_name, links_scraped
):
    """
    Call the AI agent to perform tasks based on the given prompt and tools.

    Args:
        prompt (str): The user's prompt.
        system_prompt (str): The system instructions for the AI.
        tools (List[Dict]): Available tools for the AI to use.
        plan (bool): Whether to create a plan before execution.
        data_points (List[Dict]): The list of data points to extract.
        entity_name (str): The name of the entity being researched.
        links_scraped (List[str]): List of already scraped links.

    Returns:
        str: The final response from the AI agent.
    """
    messages = []

    if plan:
        messages.append(
            {
                "role": "user",
                "content": (
                    system_prompt
                    + "  "
                    + prompt
                    + "  Let's think step by step, make a plan first"
                ),
            }
        )

        chat_response = chat_completion_request(
            messages, tool_choice="none", tools=tools
        )
        messages = [
            {"role": "user", "content": (system_prompt + "  " + prompt)},
            {"role": "assistant", "content": chat_response.choices[0].message.content},
        ]

    else:
        messages.append({"role": "user", "content": (system_prompt + "  " + prompt)})

    state = "running"

    for message in messages:
        pretty_print_conversation(message)

    while state == "running":
        chat_response = chat_completion_request(messages, tool_choice=None, tools=tools)

        if isinstance(chat_response, Exception):
            print("Failed to get a valid response:", chat_response)
            state = "finished"
        else:
            current_choice = chat_response.choices[0]
            messages.append(
                {
                    "role": "assistant",
                    "content": current_choice.message.content,
                    "tool_calls": current_choice.message.tool_calls,
                }
            )
            pretty_print_conversation(messages[-1])

            if current_choice.finish_reason == "tool_calls":
                tool_calls = current_choice.message.tool_calls
                for tool_call in tool_calls:
                    function = tool_call.function.name
                    arguments = json.loads(
                        tool_call.function.arguments
                    )  # Parse the JSON string to a Python dict

                    if function == "scrape":
                        result = tools_list[function](
                            arguments["url"], data_points, links_scraped
                        )
                    elif function == "update_data":
                        result = tools_list[function](
                            data_points, arguments["datas_update"]
                        )
                    elif function == "file_reader":
                        result = tools_list[function](arguments["file_url"], links_scraped)

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function,
                            "content": result,
                        }
                    )
                    pretty_print_conversation(messages[-1])

            if current_choice.finish_reason == "stop":
                state = "finished"

            # messages = memory_optimise(messages)
    return messages[-1]["content"]

@traceable(name="#1 Website domain research")
def website_search(entity_name: str, website: str, data_points, links_scraped, special_instruction):
    """
    Perform a search on the entity's website to find relevant information.

    Args:
        entity_name (str): The name of the entity being researched.
        website (str): The website URL of the entity.
        data_points (List[Dict]): The list of data points to extract.
        links_scraped (List[str]): List of already scraped links.

    Returns:
        str: The response from the AI agent after searching the website.
    """
    tools = [
        {
            "type": "function",
            "function": {
                "name": "scrape",
                "description": "Scrape a URL for information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "the url of the website to scrape",
                        }
                    },
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "file_reader",
                "description": "Get content from a file url that ends with pdf or img extension, e.g. https://xxxxx.jpg",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_url": {
                            "type": "string",
                            "description": "the url of the pdf or image file",
                        }
                    },
                    "required": ["file_url"],
                },
            },
        }
    ]

    data_keys_to_search = [
        {"name": obj["name"], "description": obj["description"]}
        for obj in data_points
        if obj["value"] is None or obj["value"] == "None"
    ]

    if len(data_keys_to_search) > 0:
        system_prompt = f"""
        you are a world class web scraper, you are great at finding information on urls;
        You will scrape pages within a website's domain to find specific data about the company/entity, but You NEVER make up links, ONLY scrape real links you found or given

        {special_instruction}

        You only use data retrieved from scraper, do not make things up;
        You DO NOT scrape the same url twice, if you already scraped a url, do not scrape it again;

        You NEVER ask user for inputs or permissions, just go ahead do the best thing possible without asking for permission or guidance;

        All result will be auto logged & saved, so your final output doesn't need to repeat info gathered, just output "All info found"
        """

        prompt = f"""
        Entity to search: {entity_name}

        Company Website: {website}

        Data points to find:
        {data_keys_to_search}
        """

        response = call_agent(
            prompt,
            system_prompt,
            tools,
            plan=True,
            data_points=data_points,
            entity_name=entity_name,
            links_scraped=links_scraped,
        )

        return response

@traceable(name="Run research")
def run_research(entity_name, website, data_points, special_instruction):
    """
    Run the complete research process for an entity.

    Args:
        entity_name (str): The name of the entity being researched.
        website (str): The website URL of the entity.
        data_points (List[Dict]): The list of data points to extract.

    Returns:
        List[Dict]: The updated data points after research.
    """
    links_scraped = []

    response1 = website_search(entity_name, website, data_points, links_scraped, special_instruction)
    # response2 = internet_search(entity_name, website, data_points, links_scraped)

    return data_points

def pretty_print_conversation(message):
    """
    Print a conversation message with color-coding based on the role.

    Args:
        message (Dict): The message to print.
    """
    role_to_color = {
        "system": "red",
        "user": "green",
        "assistant": "blue",
        "tool": "magenta",
    }

    if message["role"] == "system":
        print(colored(f"system: {message['content']}", role_to_color[message["role"]]))
    elif message["role"] == "user":
        print(colored(f"user: {message['content']}", role_to_color[message["role"]]))
    elif message["role"] == "assistant" and message.get("tool_calls"):
        print(
            colored(
                f"assistant: {message['tool_calls']}\n",
                role_to_color[message["role"]],
            )
        )
    elif message["role"] == "assistant" and not message.get("tool_calls"):
        print(
            colored(
                f"assistant: {message['content']}\n", role_to_color[message["role"]]
            )
        )
    elif message["role"] == "tool":
        print(
            colored(
                f"function ({message['name']}): {message['content']}\n",
                role_to_color[message["role"]],
            )
        )

# Dictionary of available tools
tools_list = {
    "scrape": scrape,
    "update_data": update_data,
    "file_reader": llama_parser,
}

# Function to save JSON array to a file in a pretty-printed format
def save_json_pretty(data, filename):
    """
    Save a JSON array to a file in a pretty-printed format.

    Args:
        data: The data to be saved as JSON.
        filename (str): The name of the file to save the data to.
    """
    try:
        print(f"Saving data to {filename}")
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, sort_keys=True, ensure_ascii=False)
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"An error occurred: {e}")

# REPLACE DATA BELOW FOR WEBSITE TO SCRAPE
entity_name = "china_monthly_auto_sales_data"
website = "http://www.myhomeok.com/xiaoliang/liebiao/80_30.htm" #landing page
# website = "http://www.myhomeok.com/xiaoliang/changshang/67_86.htm"
special_instruction = "This is a website that publish auto sales data by manufacturer in China. there are numerous links on the initial landing page. Each link links to separate webpage with sales data of a specific auto manufacturer, broken out by models, for a specific month. You should extract the sales data of the manufacturer's models and the total sales for that month. Only scrape the top 5 links on this page under 厂商销量, and before [第一页]. when url path is relative, assume it's from domain http://www.myhomeok.com/. do NOT explore other pages outside of domain, especially ecar168.cn. Do NOT translate data to english."

# REPLACE PYDANTIC MODEL BELOW TO DATA STRUCTURE YOU WANT TO EXTRACT
class ModelSales(BaseModel):
    model_name: str = Field(..., description="The name of the car model.")
    units_sold: int = Field(..., description="The number of units sold in the given month for the make model.")

class ManufacturerSales(BaseModel):
    month: int = Field(..., description="The month for which the sales data is reported, e.g., '10'.")
    year: int = Field(..., description="The year for which the sales data is reported, e.g., 2024.")
    manufacturer_name: str = Field(..., description="The name of the car manufacturer.")
    total_units_sold: int = Field(..., description="The total number of units sold by manufacturer in the given month.")
    models: List[ModelSales] = Field(..., description="A list of sales data for each model under this manufacturer.")

class DataPoints(BaseModel):
    manufacturers: List[ManufacturerSales] = Field(..., description="A list of sales data grouped by manufacturer.")


data_keys = list(DataPoints.__fields__.keys())
data_fields = DataPoints.__fields__

data_points = [{"name": key, "value": None, "reference": None, "description": data_fields[key].description} for key in data_keys]
# data = scrape(website, data_points, [])
data = run_research(entity_name, website, data_points, special_instruction)

# Specify the filename
filename = f"{entity_name}.json"

# Save the data
save_json_pretty(data_points, filename)
