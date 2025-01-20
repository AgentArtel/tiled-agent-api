# Tiled Documentation Agent API

The Tiled Documentation Agent API provides AI-powered assistance for Tiled Map Editor questions. It uses advanced language models to provide detailed, contextual answers about map creation, tileset management, and other Tiled-related topics.

## API Endpoint

```bash
Endpoint: https://tiled-agent-api-production.up.railway.app/api/ask
Method: POST
```

## Authentication

The API uses Bearer token authentication. Include your API token in the Authorization header:

```bash
Authorization: Bearer YOUR_API_TOKEN
```

## Request Format

### Headers
```bash
Content-Type: application/json
Authorization: Bearer YOUR_API_TOKEN
```

### Body Parameters
```json
{
  "query": "Your question about Tiled",           // Required: The question you want to ask
  "user_id": "optional_user_id",                  // Optional: Identifier for the user
  "session_id": "optional_session_id",            // Optional: Identifier for the session
  "context": "optional_context"                   // Optional: Additional context for the question
}
```

## Response Format

```json
{
  "response": "Detailed answer from the AI...",
  "source_documents": []  // Contains relevant Tiled documentation sources
}
```

## Example Usage

### Using curl
```bash
curl -X POST https://tiled-agent-api-production.up.railway.app/api/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -d '{
    "query": "How do I create a new tileset?",
    "user_id": "user123",
    "session_id": "session456",
    "context": "I am working on a 2D RPG game"
  }'
```

### Using Python
```python
import requests
import json

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
print(json.dumps(response.json(), indent=2))
```

## Example Response

```json
{
  "response": "To create a new tileset in Tiled, follow these steps:\n\n1. Go to File > New > New Tileset\n2. Choose whether to create a tileset from an existing image or create a collection of images\n3. If using an existing image:\n   - Select your image file\n   - Set the tile size (e.g., 32x32 pixels)\n   - Set the margin and spacing if needed\n4. If creating a collection:\n   - Name your tileset\n   - Choose the tile size\n   - Add images individually\n\nYou can then save the tileset as a .tsx file for reuse in other maps.",
  "source_documents": [
    "Manual > Working with Tilesets",
    "Manual > Creating a New Tileset"
  ]
}
```

## Rate Limiting

- 60 requests per minute per IP address
- 1000 requests per day per API token

## Error Codes

- 400: Bad Request - Invalid input parameters
- 401: Unauthorized - Invalid or missing API token
- 429: Too Many Requests - Rate limit exceeded
- 500: Internal Server Error - Something went wrong on our end

## Support

For API support or to report issues, please visit our GitHub repository or contact our support team.
