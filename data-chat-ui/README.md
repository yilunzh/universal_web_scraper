# Data Chat UI

A natural language interface for querying and analyzing China auto sales data using OpenAI, Next.js, and Supabase.

## Features

- **Natural Language Queries**: Ask questions in plain English about auto sales data
- **Intelligent Query Processing**: Uses OpenAI to interpret questions and generate SQL queries
- **Follow-up Questions**: System asks for clarification when queries are ambiguous
- **Dynamic Data Visualization**: Displays data in tables, bar charts, line charts, or pie charts based on the query type
- **Insights Generation**: Provides analytical insights along with raw data
- **Modern UI**: Built with Next.js and Shadcn UI components

## Tech Stack

- **Frontend**: Next.js, React, TypeScript, Tailwind CSS, Shadcn UI
- **Backend**: Next.js API Routes
- **Database**: Supabase (PostgreSQL)
- **AI**: OpenAI API
- **Data Visualization**: Recharts

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Supabase account with database containing auto sales data
- OpenAI API key

### Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd data-chat-ui
   ```

2. Install dependencies:
   ```
   npm install
   # or
   yarn install
   ```

3. Set up environment variables:
   Create a `.env.local` file with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
   ```

4. Run the development server:
   ```
   npm run dev
   # or
   yarn dev
   ```

5. Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Usage Examples

You can ask questions like:

- "What were the total sales of Tesla in 2020?"
- "Which manufacturer sold the most cars in 2021?"
- "Show me the monthly sales trend for Toyota in 2019"
- "Compare sales of BMW and Mercedes in 2022"
- "What's the market share of electric vehicles in 2021?"

If your question is unclear, the system will ask for more specifics:

- "For which year would you like to see Tesla sales?"
- "Would you like to see the data monthly or for the entire year?"

## Database Schema

The application works with the following database schema:

Table: `china_auto_sales`
- `manufacturer_name` (text): The auto manufacturer name
- `month` (integer): Month of the data (1-12)
- `year` (integer): Year of the data (2018 onwards)
- `total_units_sold` (integer): Total units sold by the manufacturer
- `model_name` (text): Name of the car model
- `model_units_sold` (integer): Units of this specific model sold

## License

[MIT License](LICENSE)
