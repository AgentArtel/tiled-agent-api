# Advanced Crafting System with AI Integration Design
*Design Date: 2025-01-20*

## Original Request
> I need to implement a crafting system where players can create items by interacting with an object api event to generate an item and get an item added to their Inventory. When crafting a new item is triggered by a player, it should make an API call to an n8n webhook that is a game asset and image generator with the prompt and image requirements to generate the game asset and upload it to Cloudinary and use its image editing URL magic to provide a URL for the image that is compatible with RPGJS. Players can combine items to create new ones, or pay other NPCs and provide items to AI-NPCs who will process the item on the backend to create a new item and give it back to the user. The system should support recipes, crafting stations, and different crafting categories like woodworking, smithing, and alchemy.

## System Overview
An advanced crafting system that combines Tiled Map Editor, RPGJS, and Pydantic for a complete crafting experience with AI-generated assets.

## Phase 1: Tiled Map Editor Base Structure
### Questions for Implementation:
1. How should we structure the Tiled map layers for crafting stations?
2. What custom properties do we need for crafting interactions?
3. How do we set up collision and interaction zones?
4. What object types should we define for crafting stations?

## Phase 2: RPGJS Core Implementation
### Questions for Implementation:
1. How do we implement the basic crafting station class?
2. What events do we need for player-station interaction?
3. How do we handle inventory management?
4. How do we structure the crafting menu UI?

## Phase 2.1: RPGJS-Tiled Integration
### Questions for Implementation:
1. How do we load crafting station properties from Tiled?
2. How do we map Tiled objects to RPGJS events?
3. How do we handle interaction zones defined in Tiled?
4. How do we sync station states between Tiled and RPGJS?

## Phase 3: Pydantic Data Models
### Questions for Implementation:
1. How do we model crafting recipes?
2. How do we validate item requirements?
3. How do we structure API requests/responses?
4. How do we handle image generation parameters?

## Phase 3.1: Pydantic-Tiled Integration
### Questions for Implementation:
1. How do we validate Tiled map data using Pydantic?
2. How do we model custom properties from Tiled?
3. How do we ensure type safety for Tiled objects?
4. How do we handle map validation errors?

## Phase 3.2: Pydantic-RPGJS Integration
### Questions for Implementation:
1. How do we validate RPGJS events with Pydantic?
2. How do we ensure type safety for inventory operations?
3. How do we model crafting menu data?
4. How do we validate API responses in RPGJS?

## Phase 3.3: Full System Integration
### Questions for Implementation:
1. How do we maintain data consistency across all three systems?
2. How do we handle state synchronization?
3. How do we manage error propagation?
4. How do we implement the complete crafting workflow?

Let's start by asking about Phase 1 - Tiled Map Editor structure:

```javascript
// crafting_station.js
class CraftingStation {
    constructor(type) {
        this.type = type;
        this.setupInteraction();
    }

    setupInteraction() {
        // Basic setup for the crafting station
        this.setData({
            name: `${this.type} Station`,
            graphic: `${this.type}_station.png`,
        });

        // Handle player interaction
        this.on('action', async function(player) {
            // Open crafting menu
            const craftingMenu = new CraftingMenu(this.type);
            await craftingMenu.open();

            // When player selects recipe
            craftingMenu.on('select', async (recipe) => {
                try {
                    // Make API call to n8n webhook
                    const response = await this.callCraftingAPI(recipe);
                    
                    // Add crafted item to inventory
                    if (response.success) {
                        player.addItem(response.item);
                        // Remove used materials
                        recipe.materials.forEach(material => {
                            player.removeItem(material.id, material.quantity);
                        });
                    }
                } catch (error) {
                    console.error('Crafting API call failed:', error);
                }
            });
        });
    }

    async callCraftingAPI(recipe) {
        // Make API call to n8n webhook
        const response = await fetch('YOUR_N8N_WEBHOOK_URL', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recipe: recipe,
                type: this.type,
                timestamp: Date.now()
            })
        });
        return await response.json();
    }
}

// Initialize different crafting stations
const stations = {
    woodworking: new CraftingStation('woodworking'),
    smithing: new CraftingStation('smithing'),
    alchemy: new CraftingStation('alchemy')
};
```

```python
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Dict

# 1. Crafting Recipe Models
class Requirement(BaseModel):
   tool: str = Field(..., description="Tool required for crafting")
   amount: int = Field(..., description="Number of this tool required")

class Ingredient(BaseModel):
   item: str = Field(..., description="Name of the ingredient")
   quantity: int = Field(..., description="Quantity of the ingredient")

class CraftingRecipe(BaseModel):
    ingredients: List[Ingredient] = Field(..., description="List of ingredients")
    results: str = Field(..., description="Result of the crafting")
    requirements: List[Requirement] = Field(..., description="List of requirements for crafting")

# 2. Item Generation Request Models
class ImageRequirements(BaseModel):
    height: int = Field(..., description="Image height requirement")
    width: int = Field(..., description="Image width requirement")

class ItemGenerationRequest(BaseModel):
    prompt: str = Field(..., description="Prompt for generating item")
    image_requirements: ImageRequirements = Field(..., description="Image Requirements")

# 3. API Response Models
class ItemData(BaseModel):
    item_name: str = Field(..., description="Name of the item")
    description: str = Field(..., description="Description of the item")

class APIResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    item_data: ItemData = Field(None, description="Data about the item, if successful")
    image_url: str = Field(None, description="URL of the image, if successful")
    error: str = Field(None, description="Error message, if request was unsuccessful")

# Webhook Payload Validation
class WebhookPayload(BaseModel):
    item_id: str = Field(..., description="ID of the item")
    image_url: HttpUrl = Field(..., description="URL of the image generated")
    success: bool = Field(..., description="Whether generation was successful")
