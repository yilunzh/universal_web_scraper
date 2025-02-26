import openai
import re, time, os
from firecrawl import FirecrawlApp
from dotenv import load_dotenv
import json
from tenacity import retry, wait_random_exponential, stop_after_attempt,  retry_if_exception_type
from termcolor import colored
import tiktoken
from langsmith import traceable
from langsmith.wrappers import wrap_openai
import tempfile, requests
from openai import OpenAI
import subprocess
import asyncio
import aiohttp
from aiohttp import ClientTimeout
from asyncio import Semaphore
from typing import List, Optional, Dict, Any, Type, get_type_hints, Union

import instructor
from pydantic import BaseModel, Field, create_model
import pdb
import csv
import json
import signal
from functools import wraps
import logging

# Load environment variables
load_dotenv()

# Load environment variables from .env.local
load_dotenv('.env.local')

# Initialize OpenAI client with LangSmith wrapper and instructor
client = wrap_openai(openai.Client())
instructor_client = instructor.from_openai(client, mode=instructor.Mode.TOOLS)

# Constants
GPT_MODEL = "gpt-4o"
max_token = 100000
llama_api_key = os.getenv("LLAMA_API_KEY")

# Initialize FirecrawlApp with API key from environment
firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
if not firecrawl_api_key:
    raise ValueError("FIRECRAWL_API_KEY not found in environment variables")

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
    Update the state with new data points found and save to file.

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
                    obj["reference"] = data["reference"] if data["reference"] else "None"

                    if data["type"].lower() == "list":
                        # Handle list type specially
                        data_value = json.loads(data["value"]) if isinstance(data["value"], str) else data["value"]
                        for item in data_value:
                            item["reference"] = data["reference"]

                        if obj["value"] is None:
                            obj["value"] = data_value
                        else:
                            obj["value"].extend(data_value)
                    else:
                        # Handle other types (dict, str, int) uniformly
                        obj["value"] = json.loads(data["value"]) if data["type"].lower() == "dict" else data["value"]

        # Save interim updates to file
        save_json_pretty(data_points, f"{entity_name}.json")
        return "data updated and saved"
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

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Scraping operation timed out")

@traceable(run_type="tool", name="Scrape")
@retry(
    wait=wait_random_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(3),
    retry=(retry_if_exception_type(TimeoutError) | retry_if_exception_type(Exception))  # Explicitly specify which exceptions to retry
)

def scrape(url, data_points, links_scraped):
    """
    Scrape a given URL and extract structured data with retry logic and timeout.

    Args:
    url (str): The URL to scrape.
    data_points (List[Dict]): The list of data points to extract.
    links_scraped (List[str]): List of already scraped links.

    Returns:
    dict: The extracted structured data or an error message.
    """
    app = FirecrawlApp()

    try:
        # Add delay between requests to avoid overwhelming the server
        time.sleep(2)

        # Set up the timeout signal
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(120)  # Set timeout for 120 seconds

        try:
            # Set longer timeout in FirecrawlApp configuration if possible
            scraped_data = app.scrape_url(url)  # Adjust timeout as needed

            if scraped_data["metadata"]["statusCode"] == 200:
                markdown = scraped_data["markdown"][: (max_token * 2)]
                links_scraped.append(url)

                extracted_data = extract_data_from_content(markdown, data_points, links_scraped, url)

                # Clear the alarm
                signal.alarm(0)
                return extracted_data
            else:
                status_code = scraped_data["metadata"]["statusCode"]
                print(f"HTTP Error {status_code} while scraping URL: {url}")

                # Don't retry for 404s (page not found) as they're unlikely to succeed
                if status_code == 404:
                    print("Page not found - skipping retry")
                    signal.alarm(0)  # Clear the alarm
                    return {"error": f"Page not found (404) for URL: {url}"}

                # For other status codes, raise an exception to trigger retry
                raise Exception(f"HTTP {status_code} error")

        except TimeoutError as e:
            print(f"Timeout while scraping URL {url}")
            print(f"Attempt will be retried...")
            raise  # Re-raise to trigger retry

        finally:
            # Ensure the alarm is cleared even if an exception occurs
            signal.alarm(0)

    except Exception as e:
        print(f"Error scraping URL {url}")
        print(f"Exception: {e}")

        # Don't retry if we already determined it's a 404
        if "404" in str(e):
            return {"error": f"Page not found (404) for URL: {url}"}

        print(f"Attempt will be retried...")
        raise  # Re-raise the exception to trigger retry

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

    return [data_points, links_scraped]

def generate_paginated_urls(base_url: str, num_pages: int, start_page: int = 0) -> list:
    """
    Generate a list of paginated URLs by incrementing the offset by 30.

    Args:
        base_url (str): The base URL with format 'http://www.myhomeok.com/xiaoliang/liebiao/80_0.htm'
        num_pages (int): Number of pages to generate URLs for
        start_page (int): The page number to start from (default: 0)

    Returns:
        list: List of URLs with incremented pagination values
    """
    urls = []
    base_path = base_url.rsplit('_', 1)[0]  # Split at last underscore to get 'http://www.myhomeok.com/xiaoliang/liebiao/80'

    for page in range(start_page, start_page + num_pages):
        offset = page * 30
        current_url = f"{base_path}_{offset}.htm"
        urls.append(current_url)

    return urls

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

# Function to save JSON array to a file in a pretty-printed format, loading and merging with existing data if present.
def save_json_pretty(data, filename):
    """
    Save a JSON object to a file in a pretty-printed format, loading and merging with existing data if present.
    The 'value' field contains an array of manufacturer data.
    """
    try:
        # Load existing data if file exists
        existing_data = {}
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as file:
                    file_content = file.read()
                    if file_content.strip():  # Check if file is not empty
                        existing_data = json.loads(file_content)
                    print(f"Loaded existing data: {len(existing_data.get('value', [])) if existing_data else 0} records")
            except json.JSONDecodeError as e:
                print(f"Error reading existing file: {e}. Starting fresh.")
                existing_data = {}

        # Initialize the structure if it doesn't exist
        if not existing_data:
            existing_data = {
                "description": "A list of sales data grouped by manufacturer.",
                "name": "manufacturers",
                "reference": None,
                "value": []
            }

        # Create a dictionary of existing manufacturer records for easy lookup and update
        existing_records = {}
        for idx, mfr in enumerate(existing_data['value']):
            if all(key in mfr for key in ['manufacturer_name', 'month', 'year']):
                key = (mfr['manufacturer_name'], mfr['month'], mfr['year'])
                existing_records[key] = idx

        # Process new records
        for new_record in data:
            if 'value' in new_record and isinstance(new_record['value'], list):
                for mfr in new_record['value']:
                    if all(key in mfr for key in ['manufacturer_name', 'month', 'year']):
                        key = (mfr['manufacturer_name'], mfr['month'], mfr['year'])

                        if key in existing_records:
                            existing_idx = existing_records[key]
                            existing_record = existing_data['value'][existing_idx]

                            # Update the record if new data has models or if existing record lacks models
                            if 'models' in mfr or 'models' not in existing_record:
                                existing_data['value'][existing_idx].update(mfr)
                        else:
                            # Add new record if it doesn't exist
                            existing_data['value'].append(mfr)
                            existing_records[key] = len(existing_data['value']) - 1

        print(f"Saving data with {len(existing_data['value'])} manufacturers to {filename}")
        with open(filename, "w", encoding="utf-8") as file:
            json.dump(existing_data, file, indent=4, sort_keys=True, ensure_ascii=False)
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"An error occurred while saving: {str(e)}")
        print(f"Data type: {type(data)}")
        print(f"Data preview: {str(data)[:200]}")

def export_to_csv(json_file_path: str, csv_file_path: str):
    """
    Transform JSON sales data into CSV format where each row represents monthly sales of a specific model.

    Args:
        json_file_path (str): Path to the input JSON file
        csv_file_path (str): Path to save the output CSV file
    """

    # Read JSON file
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Open CSV file for writing
    with open(csv_file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)

        # Write header
        writer.writerow(['manufacturer', 'model_name', 'month', 'year', 'units_sold'])

        # Process each manufacturer's data
        for manufacturer in data.get('value', []):
            manufacturer_name = manufacturer.get('manufacturer_name')
            month = manufacturer.get('month')
            year = manufacturer.get('year')
            reference = manufacturer.get('reference')

            # Write each model's sales data
            for model in manufacturer.get('models', []):
                writer.writerow([
                    manufacturer_name,
                    model.get('model_name'),
                    month,
                    year,
                    model.get('units_sold'),
                    reference
                ])

def check_url_status(url: str, cache: dict = {}) -> bool:
    """
    Check if a URL is accessible (not 404), using cache to avoid repeated checks.

    Args:
        url (str): URL to check
        cache (dict): Cache of previously checked URLs

    Returns:
        bool: True if URL is accessible, False if 404 or other error
    """
    if url in cache:
        return cache[url]

    try:
        response = requests.head(url, timeout=5)

        # Some servers don't support HEAD, try GET if HEAD fails
        if response.status_code == 405:  # Method not allowed
            response = requests.get(url, timeout=5)

        result = response.status_code == 200
        cache[url] = result
        return result

    except requests.RequestException as e:
        cache[url] = False
        return False

def find_first_valid_month_code(manufacturer_code: int, start_month: int = 1) -> int:
    """
    Find the first month code where the URL is valid using exponential search
    followed by binary search to minimize URL checks.

    Args:
        manufacturer_code (str): The manufacturer code to check
        start_month (int): The month code to start searching from (default: 1)

    Returns:
        int: The first valid month code, or -1 if none found
    """
    base_url = "http://www.myhomeok.com/xiaoliang/changshang/{}_{}.htm"
    cache = {}  # URL check cache

    # First check if start_month is valid
    if check_url_status(base_url.format(manufacturer_code, start_month), cache):
        return start_month

    # Exponential search forward to find upper bound
    bound = 1
    first_valid = None
    while bound < 200:  # reasonable upper limit
        month = start_month + bound
        url = base_url.format(manufacturer_code, month)
        if check_url_status(url, cache):
            first_valid = month
            # Don't break - continue searching for potentially earlier valid months
        bound *= 2

    if first_valid is None:
        return -1

    # Binary search within found bounds
    left = start_month
    right = first_valid  # End at the first valid month we found

    while left < right:
        mid = (left + right) // 2
        url = base_url.format(manufacturer_code, mid)

        if check_url_status(url, cache):
            right = mid  # Found a valid month, look for earlier ones
        else:
            left = mid + 1

    # Check the final left value
    if check_url_status(base_url.format(manufacturer_code, left), cache):
        return left

    return first_valid  # Fall back to the first valid month we found during exponential search

def find_last_valid_month_code(manufacturer_code: int, max_month: int = 200) -> int:
    """
    Find the last month code where the URL is valid by searching backwards from max_month
    using exponential search followed by binary search to minimize URL checks.

    Args:
        manufacturer_code (str): The manufacturer code to check
        max_month (int): The maximum month code to start searching from (default: 200)

    Returns:
        int: The last valid month code, or -1 if none found
    """
    base_url = "http://www.myhomeok.com/xiaoliang/changshang/{}_{}.htm"
    cache = {}  # URL check cache

    # First check if max_month is valid
    if check_url_status(base_url.format(manufacturer_code, max_month), cache):
        return max_month

    # Exponential search backwards from max_month
    bound = 1
    last_valid = None
    while bound <= max_month:
        month = max_month - bound
        if month <= 0:  # Don't check negative months
            break
        url = base_url.format(manufacturer_code, month)
        if check_url_status(url, cache):
            last_valid = month
            break  # Found a valid month, can start binary search
        bound += 10

    if last_valid is None:
        return -1

    # Binary search within found bounds
    left = max_month - bound  # Lower bound
    right = max_month - (bound // 2)  # Upper bound

    while left < right:
        mid = (left + right + 1) // 2
        url = base_url.format(manufacturer_code, mid)
        # print(bound, left, right, mid, last_valid)

        if check_url_status(url, cache):
            left = mid  # Found a valid month, look for later ones
        else:
            right = mid - 1


    # Check the final left value
    if check_url_status(base_url.format(manufacturer_code, left), cache):
        return left

    return last_valid  # Fall back to the last valid month we found during exponential search

def generate_urls_from_codes(manufacturer_csv_path: str, month_csv_path: str) -> list:
    """
    Generate URLs by combining manufacturer codes and month codes from CSV files.

    Args:
        manufacturer_csv_path (str): Path to CSV file containing manufacturer codes
        month_csv_path (str): Path to CSV file containing month codes

    Returns:
        list: List of generated URLs in the format
              'http://www.myhomeok.com/xiaoliang/changshang/{manufacturer_code}_{month_code}.htm'
    """
    urls = []
    base_url = "http://www.myhomeok.com/xiaoliang/changshang/{}_{}.htm"

    try:
        # Read manufacturer codes
        with open(manufacturer_csv_path, 'r', encoding='utf-8') as f:
            manufacturer_reader = csv.DictReader(f)
            manufacturer_codes = [int(row['manufacturer_code']) for row in manufacturer_reader]

        # Read month codes
        with open(month_csv_path, 'r', encoding='utf-8') as f:
            month_reader = csv.DictReader(f)
            month_codes = [int(row['month_year_code']) for row in month_reader]

        # Generate URLs by combining codes
        for mfr_code in manufacturer_codes:
            if mfr_code in range(61,62):
                first_valid_month = find_first_valid_month_code(mfr_code, 1)
                last_valid_month = find_last_valid_month_code(mfr_code, max(month_codes))
                for month_code in range(first_valid_month, last_valid_month + 1):
                    url = base_url.format(mfr_code, month_code)
                    urls.append(url)

        print(f"Generated {len(urls)} URLs")
        return urls

    except FileNotFoundError as e:
        print(f"Error: Could not find one of the CSV files - {e}")
        return []
    except Exception as e:
        print(f"Error while processing CSV files: {e}")
        return []

def validate_entry(entry, url):
    with open('manufacturer_code.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)
        manufacturer_lookup = {int(row[0]): row[1] for row in reader}

    found_mismatch = False

    url_parts = url.split('/')[-1].split('_')
    manufacturer_code = int(url_parts[0])
    month_code = int(url_parts[1].split('.')[0])

    expected_name = manufacturer_lookup.get(manufacturer_code)

    print(f"Validating entry for {url}")
    print(f"Entry: {entry}")
    print(f"Expected name: {expected_name}")
    print(f"Current name: {entry.get('manufacturer_name')}")

    if expected_name and entry.get("manufacturer_name") != expected_name:
        print(f"Mismatch found for {url}")
        print(f"Current: {entry.get('manufacturer_name')}")
        print(f"Expected: {expected_name}")
        found_mismatch = True
        print("-" * 50)

    return not found_mismatch  # Return True if validation passes (no mismatch)


def send_mac_notification(title, message):
    """
    Send a push notification on macOS.
    
    Args:
        title (str): The notification title
        message (str): The notification message
    """
    apple_script = f'display notification "{message}" with title "{title}"'
    subprocess.run(['osascript', '-e', apple_script])

# def validate_and_update_data():
#     updated = False

#     while True:  # Keep checking until no more updates needed
#         # Read current state of file
#         with open('china_monthly_auto_sales_data_v2.json', 'r', encoding='utf-8') as f:
#             data = json.load(f)

#         with open('manufacturer_code.csv', 'r', encoding='utf-8') as f:
#             reader = csv.reader(f)
#             next(reader)
#             manufacturer_lookup = {int(row[0]): row[1] for row in reader}

#         entries = data["value"]
#         found_mismatch = False

#         for i, entry in enumerate(entries):
#             url_parts = entry["reference"].split('/')[-1].split('_')
#             manufacturer_code = int(url_parts[0])
#             month_code = int(url_parts[1].split('.')[0])

#             expected_name = manufacturer_lookup.get(manufacturer_code)
#             if expected_name and entry["manufacturer_name"] != expected_name:
#                 print(f"Mismatch found for {entry['reference']}")
#                 print(f"Current: {entry['manufacturer_name']}")
#                 print(f"Expected: {expected_name}")

#                 # Re-scrape the URL first
#                 data_points = [{"name": key, "value": None, "reference": None, "description": data_fields[key].description} for key in data_keys]
#                 new_data = scrape(entry["reference"], data_points, [])

#                 if new_data and len(new_data) > 0 and 'manufacturers' in new_data[0]:
#                     manufacturer_data = new_data[0]['manufacturers'][0]

#                     # Update the entry in place
#                     entries[i].update({
#                         'manufacturer_name': expected_name,
#                         'models': manufacturer_data.get('models', []),
#                         'total_units_sold': manufacturer_data.get('total_units_sold', 0),
#                         'month': manufacturer_data.get('month', month_code),
#                         'year': manufacturer_data.get('year', 2024)
#                     })

#                     data["value"] = entries

#                     # Save the updated data
#                     with open('china_monthly_auto_sales_data_v2.json', 'w', encoding='utf-8') as f:
#                         json.dump(data, f, ensure_ascii=False, indent=2)
#                     print(f"Updated entry in place")

#                     updated = True
#                     found_mismatch = True
#                 print("-" * 50)
#                 break  # Exit the loop after handling one mismatch

#         if not found_mismatch:  # No more mismatches found
#             break

#     if updated:
#         print("Completed all updates")

# Example usage:
# urls = generate_urls_from_codes('manufacturer_code.csv', 'month_code.csv')

# REPLACE DATA BELOW FOR WEBSITE TO SCRAPE
# entity_name = "china_monthly_auto_sales_data"
# entity_name = "china_monthly_auto_sales_data_v2"

# entity_name = 'tesla_nov_2024_sales_data'
website = "http://www.myhomeok.com/xiaoliang/liebiao/80_30.htm" #landing page
monthly_sales_page = "http://www.myhomeok.com/xiaoliang/changshang/104_86.htm"
"http://www.myhomeok.com/xiaoliang/changshang/{manufacturer_code}_{month_code}.htm"
special_instruction = '''
This is a website that publish auto sales data by manufacturer in China. You are asked to extract monthly sales data of each manufacturer by model. You do this in 2 steps.
Step 1: There are numerous links on the monthly sales page. Only scrape links on this page under 厂商销量, and before [第一页]. There should be 30 results for each sales page. You should extract those links.
Step 2: Each of the extracted link links to separate webpage with specific auto manufacturer, broken out by models, for a specific month (manufacturer monthly sales page).
For each manufacturer monthly sales page, you should extract the sales data of the manufacturer's models and the total sales for that month.
when url path is relative, assume it's from domain http://www.myhomeok.com/. do NOT explore other pages outside of domain, especially ecar168.cn.
# Important: DO NOT translate any Chinese names to English. Keep all manufacturer and model names in their original Chinese characters.
'''

monthly_sales_page_instruction = '''
This is a website that publish auto sales data by manufacturer in China. You are asked to extract monthly sales data of each manufacturer by model.
The url displays sales data of specific auto manufacturer, broken out by models, for a specific month (manufacturer monthly sales page).
For each manufacturer monthly sales page, you should extract the sales data of the manufacturer's models and the total sales for that month.
when url path is relative, assume it's from domain http://www.myhomeok.com/. do NOT explore other pages outside of domain, especially ecar168.cn.
# Important: DO NOT translate any Chinese names to English. Keep all manufacturer and model names in their original Chinese characters.
'''

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

class MonthlySalesUrls(BaseModel):
    manufacturer_sales_url: str = Field(..., description="The url of the manufacturer sales page to scrape")
    month: int = Field(..., description="The month for which the sales data is reported, e.g., '10'.")
    year: int = Field(..., description="The year for which the sales data is reported, e.g., 2024.")
    manufacturer_name: str = Field(..., description="The name of the car manufacturer.")
    monthly_units_sold: int = Field(..., description="The total number of units sold by manufacturer in the given month.")

async def async_scrape(url: str, data_points: List[Dict], links_scraped: List[str], semaphore: Semaphore) -> Dict:
    """
    Asynchronously scrape a given URL and extract structured data.
    
    Args:
        url (str): The URL to scrape
        data_points (List[Dict]): The list of data points to extract
        links_scraped (List[str]): List of already scraped links
        semaphore (Semaphore): Semaphore to limit concurrent requests
        
    Returns:
        Dict: The extracted structured data or an error message
    """
    app = FirecrawlApp()
    
    try:
        # Add small delay between requests
        await asyncio.sleep(1)
        
        async with semaphore:  # Limit concurrent requests
            try:
                # Use run_in_executor to run the synchronous scrape_url method asynchronously
                loop = asyncio.get_event_loop()
                scraped_data = await loop.run_in_executor(None, app.scrape_url, url)

                if scraped_data["metadata"]["statusCode"] == 200:
                    markdown = scraped_data["markdown"][: (max_token * 2)]
                    links_scraped.append(url)

                    extracted_data = extract_data_from_content(markdown, data_points, links_scraped, url)
                    # Convert JSON string to dictionary if needed
                    if isinstance(extracted_data, str):
                        try:
                            extracted_data = json.loads(extracted_data)
                        except json.JSONDecodeError:
                            return {"error": "Failed to parse JSON response"}
                    return extracted_data
                else:
                    status_code = scraped_data["metadata"]["statusCode"]
                    print(f"HTTP Error {status_code} while scraping URL: {url}")

                    if status_code == 404:
                        print("Page not found - skipping retry")
                        return {"error": f"Page not found (404) for URL: {url}"}

                    raise Exception(f"HTTP {status_code} error")

            except Exception as e:
                print(f"Error scraping URL {url}")
                print(f"Exception: {e}")
                raise

    except Exception as e:
        print(f"Failed to scrape {url}: {e}")
        return {"error": str(e)}

class ScrapingState:
    def __init__(self):
        self.links_scraped = []
        self.all_data = []
        self.results = {
            "successful": [],
            "failed": []
        }
        self.semaphore = Semaphore(5)

@traceable(run_type="chain", name="Process single URL")
async def process_url(url: str, data_points: List[Dict], filename: str, state: ScrapingState) -> None:
    """
    Process a single URL with proper error handling.
    
    Args:
        url (str): The URL to process
        data_points (List[Dict]): The data points to extract
        filename (str): The output filename
        state (ScrapingState): Shared state for the scraping process
    """
    print(f"Processing {url}")
    try:
        data = await async_scrape(url, data_points, state.links_scraped, state.semaphore)
        
        if isinstance(data, dict):
            if "manufacturers" in data and isinstance(data["manufacturers"], list):
                manufacturer_data = data["manufacturers"][0]
                try:
                    if validate_entry(manufacturer_data, url):
                        state.all_data.extend([manufacturer_data])
                        save_json_pretty(state.all_data, filename)
                        state.results["successful"].append(url)
                        print(f"Successfully processed {url}")
                    else:
                        state.results["failed"].append({"url": url, "reason": "Failed validation"})
                except Exception as save_error:
                    print(f"Error saving data for {url}: {str(save_error)}")
                    state.results["failed"].append({"url": url, "reason": f"Save error: {str(save_error)}"})
            else:
                error_msg = data.get("error", "Invalid data format - missing manufacturers data")
                state.results["failed"].append({"url": url, "reason": error_msg})
                print(f"Invalid data format for {url}: {data}")
        else:
            state.results["failed"].append({"url": url, "reason": f"Invalid response format: {type(data)}"})
            print(f"Invalid response type for {url}: {type(data)}, Data: {data}")
        
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")
        state.results["failed"].append({"url": url, "reason": str(e)})

@traceable(run_type="chain", name="Process URLs")
async def process_urls(urls: List[str], data_points: List[Dict], filename: str) -> None:
    """
    Process multiple URLs concurrently with a limit on concurrent requests.
    """
    state = ScrapingState()
    
    # Create tasks for all URLs
    tasks = [process_url(url, data_points, filename, state) for url in urls]
    
    # Process URLs concurrently
    await asyncio.gather(*tasks, return_exceptions=True)
    
    # Generate summary report
    print("\n=== Scraping Summary ===")
    print(f"Total URLs processed: {len(urls)}")
    print(f"Successful: {len(state.results['successful'])}")
    print(f"Failed: {len(state.results['failed'])}")
    
    if state.results["failed"]:
        print("\nFailed URLs and reasons:")
        for failure in state.results["failed"]:
            print(f"URL: {failure['url']}")
            print(f"Reason: {failure['reason']}")
            print("-" * 50)
    
    print(f"\nTotal records collected: {len(state.all_data)}")
    export_to_csv(filename, filename.replace('.json', '.csv'))
    
    # Save the results report
    report_filename = f"scraping_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(state.results, f, indent=4, ensure_ascii=False)
    print(f"\nDetailed report saved to {report_filename}")
    
    # Send notification
    send_mac_notification(
        "Web Scraping Complete", 
        f"Collected {len(state.all_data)} records. Success: {len(state.results['successful'])}, Failed: {len(state.results['failed'])}"
    )

def scrape_urls(urls):
    successful_urls = []
    failed_urls = []
    
    for url in urls:
        try:
            # Your scraping logic here
            successful_urls.append(url)
        except Exception as e:
            # Instead of a generic "Unknown URL"
            failed_urls.append(url)
            logging.error(f"Failed to scrape URL: {url}")
            logging.error(f"Error: {str(e)}")
    
    return successful_urls, failed_urls

def generate_summary(job_name, total_urls, successful_urls, failed_urls):
    success_rate = (len(successful_urls) / total_urls * 100) if total_urls > 0 else 0
    
    summary = f"""
                    Job Complete: {job_name}
                    =====================================
                    Total URLs processed: {total_urls}
                    Successfully scraped: {len(successful_urls)}
                    Failed: {len(failed_urls)}
                    Success rate: {success_rate:.1f}%
                    
                    Failed URLs ({len(failed_urls)}): [
                    {"".join(f"    {url}\n" for url in failed_urls)}]
                    """
    return summary

#validation code
first_month = find_first_valid_month_code(62)
print(first_month)
last_month = find_last_valid_month_code(62, 86)
print(last_month)

# entity_name = 'tesla_nov_2024_sales_data'
# filename = f"{entity_name}.json"
# monthly_sales_page = "http://www.myhomeok.com/xiaoliang/changshang/7_41.htm"
# print(scrape(monthly_sales_page, data_points, []))

# # Clear the alarm
# signal.alarm(0)
# return extracted_data

