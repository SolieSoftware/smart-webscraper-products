# Smart Web Scraper - AI-Powered Product Information Extraction

An intelligent web scraping system that leverages AI agents to automatically discover and extract product information (names, prices, images) from company websites based on natural language prompts.

## Features

- **Natural Language Interface**: Simply describe what you want to scrape (e.g., "Retrieve Clothing products in the UK")
- **Autonomous Discovery**: Automatically finds relevant e-commerce websites using search APIs
- **Intelligent Extraction**: Uses LLM (GPT-4/Claude) to extract product data from diverse website structures
- **Image Management**: Downloads and stores product images locally
- **Persistent Storage**: Saves all data to PostgreSQL database
- **Ethical Scraping**: Respects rate limits, uses delays, and identifies user agent

## Architecture

Built with:
- **LangChain**: Agent orchestration and tool integration
- **Playwright**: Browser automation for dynamic content
- **PostgreSQL**: Product data persistence
- **OpenAI/Anthropic**: LLM for intelligent extraction
- **SerpAPI**: Search engine integration

## Project Structure

```
smart-webscraper-products/
├── src/
│   ├── agents/          # LangChain agent and tools
│   ├── scrapers/        # Playwright browser management
│   ├── extractors/      # LLM-based data extraction
│   ├── search/          # Search API integration
│   ├── storage/         # Database and image storage
│   └── config/          # Configuration management
├── data/
│   └── images/          # Downloaded product images
├── alembic/             # Database migrations
├── main.py              # CLI entry point
└── requirements.txt     # Python dependencies
```

## Setup

### Prerequisites

- Python 3.10 or higher
- PostgreSQL database
- API keys:
  - OpenAI API key OR Anthropic API key
  - SerpAPI key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd smart-webscraper-products
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install chromium
```

5. Set up PostgreSQL database:
```bash
# Create database
createdb webscraper_products

# Or use psql
psql -U postgres -c "CREATE DATABASE webscraper_products;"
```

6. Configure environment variables:
```bash
# Copy the example env file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

Required environment variables in `.env`:
```env
# LLM API Keys (at least one required)
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Search API
SERPAPI_API_KEY=your_serpapi_key_here

# Database
DATABASE_URL=postgresql://username:password@localhost:5432/webscraper_products

# Optional Settings
IMAGE_STORAGE_PATH=data/images
MAX_RETRIES=3
REQUEST_DELAY=2.0
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.0
```

7. Initialize the database:
```bash
python main.py --init-db "test query"
```

Or use Alembic migrations:
```bash
alembic upgrade head
```

## Usage

### Basic Usage

Run the scraper with a natural language prompt:

```bash
python main.py "Retrieve Clothing products in the UK"
```

### More Examples

```bash
# Find electronics from US retailers
python main.py "Find electronics from US retailers"

# Search for furniture stores in Canada
python main.py "Search for furniture stores in Canada"

# Get sports equipment from online shops
python main.py "Get sports equipment from online shops"
```

### Command Line Options

```bash
python main.py --help

Options:
  --init-db    Initialize/reset the database before scraping
  --verbose    Enable verbose debug logging
  -v           Short form of --verbose
```

### Example with Options

```bash
# Initialize DB and run with verbose logging
python main.py --init-db --verbose "Retrieve Clothing products in the UK"
```

## How It Works

1. **Search Phase**: The agent uses SerpAPI to find relevant company websites based on your prompt
2. **Scraping Phase**: For each website, Playwright navigates and extracts HTML content
3. **Extraction Phase**: LLM analyzes the HTML and extracts structured product data
4. **Storage Phase**: Products are saved to PostgreSQL and images are downloaded locally

## Database Schema

Products are stored with the following fields:

```sql
CREATE TABLE products (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    price DECIMAL(10,2),
    currency VARCHAR(3),
    image_paths JSONB,
    source_url TEXT NOT NULL,
    company_name VARCHAR(255),
    scraped_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB
);
```

### Querying Scraped Data

```sql
-- View all products
SELECT name, price, currency, company_name, scraped_at
FROM products
ORDER BY scraped_at DESC;

-- Products from a specific company
SELECT * FROM products WHERE company_name = 'CompanyName';

-- Products in a price range
SELECT * FROM products WHERE price BETWEEN 10 AND 50;

-- Count products by company
SELECT company_name, COUNT(*) as product_count
FROM products
GROUP BY company_name;
```

## Configuration

All configuration is managed through environment variables in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | None |
| `ANTHROPIC_API_KEY` | Anthropic API key | None |
| `SERPAPI_API_KEY` | SerpAPI key (required) | None |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://localhost:5432/webscraper_products` |
| `IMAGE_STORAGE_PATH` | Directory for downloaded images | `data/images` |
| `MAX_RETRIES` | Max retry attempts for failed requests | `3` |
| `REQUEST_DELAY` | Delay between requests (seconds) | `2.0` |
| `LLM_MODEL` | LLM model to use | `gpt-4` |
| `LLM_TEMPERATURE` | LLM temperature | `0.0` |

## Troubleshooting

### Database Connection Errors

If you see database connection errors:

1. Ensure PostgreSQL is running:
```bash
# Check status
pg_ctl status

# Start PostgreSQL (macOS with Homebrew)
brew services start postgresql

# Start PostgreSQL (Linux)
sudo systemctl start postgresql
```

2. Verify database exists:
```bash
psql -l | grep webscraper_products
```

3. Check connection string in `.env`

### Playwright Issues

If Playwright fails to launch:

```bash
# Reinstall browsers
playwright install --force chromium

# Or install system dependencies (Linux)
playwright install-deps
```

### API Key Errors

Ensure your API keys are correctly set in `.env`:

```bash
# Test OpenAI key
python -c "import openai; openai.api_key='your_key'; print('OK')"

# Check environment loading
python -c "from src.config import settings; print(settings.get_llm_provider())"
```

### No Products Found

If scraping returns no products:

1. Check that the search query finds relevant e-commerce sites
2. Try more specific queries (e.g., "Nike shoes UK" vs "clothing")
3. Enable verbose logging to see what's happening:
```bash
python main.py --verbose "your query"
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Database Migrations

Create a new migration after changing models:

```bash
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

### Logging

Logs are written to:
- Console (stdout)
- `scraper.log` file

Adjust logging level in `main.py` or use `--verbose` flag.

## Ethical Considerations

This tool is designed for legitimate use cases:
- Market research
- Price comparison
- Product catalog aggregation
- Competitive analysis

**Please ensure you:**
- Have permission to scrape target websites
- Respect robots.txt files
- Use reasonable rate limits
- Comply with website terms of service
- Follow data protection regulations (GDPR, etc.)

The scraper includes built-in delays and respects standard web etiquette.

## Limitations

- Relies on LLM accuracy for extraction (may miss or misinterpret data)
- Search API has rate limits (SerpAPI: 100 searches/month free tier)
- Some websites use advanced anti-bot protection
- Image downloads may fail for CDN-protected images
- Best results with standard e-commerce HTML structures

## Future Enhancements

Potential improvements:
- Multi-threading for parallel scraping
- Agent memory to avoid duplicate scrapes
- Advanced filtering (price range, brands, categories)
- Export functionality (CSV, JSON)
- Web UI for viewing products
- Scheduled/automated scraping
- Vector embeddings for semantic search

## License

[Add your license here]

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Support

For issues or questions:
- Check the troubleshooting section
- Review logs with `--verbose` flag
- Open an issue on GitHub

## Acknowledgments

Built with:
- [LangChain](https://github.com/langchain-ai/langchain)
- [Playwright](https://playwright.dev/)
- [OpenAI](https://openai.com/) / [Anthropic](https://anthropic.com/)
- [SerpAPI](https://serpapi.com/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
