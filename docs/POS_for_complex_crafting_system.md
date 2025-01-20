# POS for Complex Crafting System

**Document Name:** `POS_for_complex_crafting_system.md`  
**Purpose:** Provide a structured plan for implementing and iterating on the advanced crafting system, guiding the AI agents to ask the right questions and document responses step-by-step.

## Overview

We're building a "complex crafting system" for an RPGJS-based game. The system will:
1. Let players interact with a **crafting station** in-game.
2. Trigger an **n8n webhook** call to generate or transform items (the n8n workflow when requested by a user creates a new item and triggers a post request to create the item asset).
3. The generated asset is uploaded to Cloudinary making the image accessible via URL so the item can visually appear in game.
4. Return updated items or brand-new items to the player's inventory with appropriate success/fail messages:
   - Success: "Item was added to your inventory"
   - Fail: "We have a problem, here's what went wrong"

## Phase 1: Single Basic Crafting Station in Tiled

### Context
- Create one crafting station in Tiled.
- Test the n8n webhook with a single item-generation flow (prompt -> AI -> Cloudinary -> item URL).
- Validate that the game properly spawns the station and the player can craft.

### Questions to Ask Agents
1. **Tiled Setup**  
   - "How do we organize layers and objects in Tiled for a basic crafting station?"  
   - "What custom properties do we need for collision vs. interaction?"  
   - "Should the station be an Object layer or a Tile layer for easier event mapping in RPGJS?"

#### Agent Responses

Question 1: "How do we organize layers and objects in Tiled for a basic crafting station?"

Agent Response:
The RPGJS agent provided a detailed structure for organizing layers and objects in Tiled:

1. **Layer Structure:**
   - **Tiles Layer:** Contains the visual representation or tile for the crafting station
   - **Object Layer:** Dedicated layer for interactive zones and functionality

2. **Collision Setup:**
   - Draw a polygon or rectangle around the crafting station in the object layer
   - This defines where the player can interact with the station

3. **Custom Properties for Crafting Station:**
```json
{
    "name": "Crafting Station",
    "type": "craftingStation",
    "properties": {
        "interaction": true,
        "craftingStation": true
    }
}
```

4. **Integration Code Example:**
```javascript
async function triggerWebhookAndFetchImage(webhookURL, imageURL) {
    // Call webhook for item generation
    await fetch(webhookURL, {
        method: 'POST'
    });

    // Fetch image from Cloudinary URL
    const response = await fetch(imageURL);
    const blob = await response.blob();
    const image = URL.createObjectURL(blob);
    // Display image here
}
```

**Important Notes:**
- RPGJS doesn't natively support external image loading - need plugin or custom functionality
- Consider performance when fetching images at runtime
- Recommended to use server-side service for webhook interactions
- Handle errors and edge cases for external service dependencies

Question 2: "What specific properties do we need for different crafting station types?"

RPGJS Agent Response:
1. **Interaction Zones Setup:**
```javascript
// Access different station areas
let woodworkingArea = tiledMap.objectGroup.findObjectsByType('woodworking_area');
let smithingArea = tiledMap.objectGroup.findObjectsByType('smithing_area');

// Example station properties
let woodworkingStation = tiledMap.objectGroup.findObjectByName('woodworking_station');
let toolRequired = woodworkingStation.properties['tool_required'];
let skillLevel = woodworkingStation.properties['skill_level'];

// Access craftable items
let smithingStation = tiledMap.objectGroup.findObjectByName('smithing_station');
let craftableItems = JSON.parse(smithingStation.properties['craftable_items']);
```

Pydantic Agent Response:
The Pydantic agent provided a data model structure for validating station properties:

```python
from typing import Optional, List
from pydantic import BaseModel

class InteractionZone(BaseModel):
    x: float
    y: float
    width: float
    height: float

class CraftingStation(BaseModel):
    station_type: str
    interaction_zone: InteractionZone
    required_skill_level: int  

class WoodWorkingStation(CraftingStation):
    tools_required: List[str]
    allowed_recipes: List[str]

class SmithingStation(CraftingStation):
    tools_required: List[str]
    allowed_recipes: List[str]

class AlchemyStation(CraftingStation):
    tools_required: List[str]
    allowed_recipes: List[str]
```

**Combined Implementation Strategy:**
1. Define station types in Tiled with specific properties:
   - `station_type`: (woodworking, smithing, alchemy)
   - `tool_required`: List of required tools
   - `skill_level`: Required skill level
   - `craftable_items`: JSON array of available recipes

2. Use Pydantic models to validate:
   - Station configuration when loading from Tiled
   - Recipe requirements before crafting
   - API responses from n8n webhook

3. Use RPGJS to:
   - Load and parse station properties from Tiled
   - Handle player interactions with stations
   - Manage inventory updates after crafting

Next Question: "How do we structure the crafting menu UI in RPGJS to display available recipes and requirements?"

Question 3: "How do we structure the crafting menu UI in RPGJS?"

RPGJS Agent Response:
The agent provided a comprehensive approach to building the crafting UI:

1. **Station Type and Recipe Display:**
```javascript
StationType = {
    crafting: {
        recipes: ["Recipe1", "Recipe2",...]
    },
    // Other station types...
}

Recipe = {
    name: "Recipe1",
    ingredients: ["Ingredient1", "Ingredient2",...],
    tools: ["Tool1", "Tool2",...]
}
```

2. **UI Components Needed:**
   - Recipe list display
   - Ingredient/tool requirements panel
   - Crafting button
   - Success/failure message display
   - Generated item image display

3. **Image Display Integration:**
```javascript
let sprite = new PIXI.Sprite.from('YOUR_IMAGE_URL');
app.stage.addChild(sprite);
```

Pydantic Agent Response:
The agent provided a data validation structure for the UI:

```python
from pydantic import BaseModel
from typing import List, Dict

class Recipe(BaseModel):
    recipe_name: str
    station_type: str
    ingredients: Dict[str, int]  # ingredient name to quantity 
    tools: List[str]
    crafting_webhook: str  # n8n webhook endpoint
    success_message: str
    failure_message: str
    product_image: str  # Cloudinary image URL

# Example usage
example_recipe = Recipe(
    recipe_name = "Iron Sword",
    station_type = "Blacksmith",
    ingredients = {"Iron Bar": 2, "Wood": 1},
    tools = ["Hammer", "Anvil"],
    crafting_webhook = "<your-n8n-webhook>",
    success_message = "Crafting Success: Iron Sword has been crafted!",
    failure_message = "Crafting Failure: Not enough ingredients.",
    product_image = "<your-Cloudinary-url>"
)
```

**Combined Implementation Strategy:**
1. **Data Flow:**
   - Load station type and available recipes from Tiled properties
   - Validate recipe data using Pydantic models
   - Display UI elements using RPGJS/PIXI
   - Handle crafting through n8n webhook
   - Update UI with Cloudinary images

2. **UI Components:**
   - Main crafting window (shows when interacting with station)
   - Recipe list (filtered by station type)
   - Requirements panel (shows ingredients/tools needed)
   - Crafting button (triggers webhook)
   - Result display (shows success/failure and item image)

3. **Error Handling:**
   - Validate all data with Pydantic before sending to webhook
   - Show clear error messages if validation fails
   - Handle network errors in webhook calls
   - Provide fallback for failed image loads

## Phase 2: RPGJS Core Implementation

Now that we have our Tiled structure and UI design, let's implement the core RPGJS functionality:

### Questions to Ask Agents
1. **Event System**
   - How do we structure the event system for crafting stations?
   - How do we handle player interaction events?
   - How do we manage the crafting process state?

Let's start with the event system structure...

Question 4: "How should we structure the RPGJS event system for crafting stations?"

RPGJS Agent Response:
The agent provided a comprehensive event system structure:

1. **Player Interaction Handling:**
```javascript
if(game.input.isPressed('interact')) {
    const craftingStation = game.getCollisions(player);
    if(craftingStation) {
        // Start crafting process
    }
}
```

2. **State Management:**
```javascript
var craftingState = "selecting recipe";

switch (craftingState) {
     case "selecting recipe":
         // Handle selecting recipe
         break;
     case "checking requirements":
         // Handle checking requirements
         break;
     case "crafting":
         // Handle crafting
         break;
}
```

3. **Webhook Integration:**
```javascript
fetch(n8nWebhookURL, {
  method: 'POST',
  body: JSON.stringify(itemData),
  headers: {'Content-Type': 'application/json'}
})
.then(response => response.json())
.then(data => console.log(data))
.catch((error) => console.error('Error:', error));
```

4. **UI Updates:**
```javascript
player.addToInventory(craftedItem);

GUI.show({
    template: 'CraftingSuccess',
    data: {
        itemName: craftedItem.name,
        itemQty: craftedItem.quantity
    }
});
```

Pydantic Agent Response:
The agent provided data validation models for each event type:

```python
from pydantic import BaseModel

class PlayerInteraction(BaseModel):
    player_id: int
    station_id: int

class Interaction(BaseModel):
    player_id: int
    workstation_id: int
    action: str  # select_recipe, check_requirements, crafting
    item_id: int = None  # Optional: for specific item crafting

class GenerateItem(BaseModel):
    player_id: int
    workstation_id: int
    crafted_item_id: int

class UpdateInventory(BaseModel):
    player_id: int
    item_id: int
    quantity: int

# Example endpoint using validation
@app.post("/playerInteraction/")
async def playerInteraction(interaction: PlayerInteraction):
    try:
        PlayerInteraction(**interaction)
    except ValidationError as e:
        print(e)
        return {'error': 'Invalid interaction data'}
    # Continue with logic
    pass
```

**Combined Implementation Strategy:**
1. **Event Flow:**
   - Player approaches station -> Trigger interaction check
   - Open crafting UI -> Load station recipes
   - Select recipe -> Validate requirements
   - Start crafting -> Call n8n webhook
   - Receive result -> Update inventory and UI

2. **State Management:**
   - Use state machine for crafting process
   - Validate state transitions with Pydantic
   - Handle errors and edge cases

3. **Data Validation:**
   - Validate all inputs/outputs with Pydantic
   - Ensure webhook data matches expected format
   - Validate inventory updates

## Phase 3: n8n Integration

Now that we have our RPGJS event system designed, let's implement the n8n webhook integration:

### Questions to Ask Agents
1. **Webhook Structure**
   - How do we structure the n8n workflow for item generation?
   - What data should be passed to/from the webhook?
   - How do we handle webhook errors and retries?

Let's start with the webhook structure...

## Phase 4: Testing and Validation

Before implementing the n8n workflow, let's ensure our core components are working correctly:

### Questions to Ask Agents
1. **Tiled Map Testing**
   - How do we validate that crafting stations are properly configured?
   - What tests should we run for collision and interaction zones?
   - How do we verify custom properties are loading correctly?

2. **RPGJS Event Testing**
   - How do we test the state machine transitions?
   - What edge cases should we handle in player interactions?
   - How do we validate inventory updates?

3. **Data Validation Testing**
   - How do we test Pydantic model validations?
   - What error cases should we handle?
   - How do we ensure data consistency across components?

Let's start with testing the Tiled map configuration...

Question 5: "How should we test the Tiled map configuration for crafting stations?"

RPGJS Agent Response:
The agent provided several testing approaches:

1. **Station Properties and Collision Zones:**
```javascript
// Iterate over all items and validate properties
eachItem(gameMap, (item) => {
    assert(item.craftingStation, 'Crafting station property missing');
    assert(item.collisionZone, 'Collision zone property missing');
});
```

2. **Event Triggering:**
```javascript
const event = game.simulateInteraction(station);
assert(event.name, 'Expected event name');
```

3. **Data Type Validation:**
```javascript
const type = itemType(gameMap, stationId);
assert(type === 'string', 'Expected station id to be a string');
```

4. **Edge Cases:**
```javascript
const station = gameMap.findOverlappingStations();
assert(station.length <= 1, 'More than one station overlapping');
```

Pydantic Agent Response:
The agent provided data validation models for testing:

```python
from pydantic import BaseModel, Field, validator
from typing import List

class CollisionZone(BaseModel):
    zone_id: str
    coordinates: List[float]  # [x1, y1, x2, y2]
    overlapping: bool = Field(default=False)

class InteractionEvent(BaseModel):
    event_id: str
    triggered: bool = Field(default=False)

class StationProperty(BaseModel):
    prop_name: str
    prop_data_type: str
    value: str  # parse to appropriate type later

class CraftingStation(BaseModel):
    station_properties: List[StationProperty]
    collision_zones: List[CollisionZone]
    interaction_zones: List[InteractionEvent]

    @validator('collision_zones', 'interaction_zones', each_item=True)
    def check_zone_overlapping(cls, zone):
        # Implement overlap checking logic
        return zone

    @validator('station_properties', each_item=True)
    def check_properties(cls, property):
        # Implement property validation
        return property
```

**Combined Testing Strategy:**
1. **Automated Tests:**
   - Use RPGJS functions to validate game mechanics
   - Use Pydantic models to validate data structures
   - Write unit tests for each component

2. **Manual Testing:**
   - Test player interactions in-game
   - Verify visual feedback
   - Check edge cases

3. **Error Handling:**
   - Validate all required properties
   - Check for overlapping zones
   - Handle missing or invalid data

Next Question: "How do we test the RPGJS event system state transitions and error handling?"
