# Tiled Documentation Agent API

An AI-powered API for answering questions about the Tiled Map Editor. This API provides detailed responses about map creation, tileset management, and other Tiled-related topics by leveraging the official Tiled documentation.

## Features

- AI-powered responses using OpenAI's language models
- Context-aware answers from official Tiled documentation
- Source references for each response
- Bearer token authentication
- CORS support
- Rate limiting

## Getting Started

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
4. Run the API locally:
   ```bash
   uvicorn tiled_agent:app --reload
   ```

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_KEY`: Your Supabase service key
- `API_BEARER_TOKEN`: Bearer token for API authentication

## API Documentation

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed API documentation.

## Deployment

This API is designed to be deployed on Railway. Follow these steps:

1. Create a new project on Railway
2. Connect your GitHub repository
3. Add the required environment variables
4. Deploy!

## Example Usage

```python
import requests

url = "https://tiled-agent-api-production.up.railway.app/api/ask"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_API_TOKEN"
}
data = {
    "query": "How do I create a new tileset?",
    "user_id": "user123",
    "session_id": "session456",
    "context": "I am working on a 2D RPG game"
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
