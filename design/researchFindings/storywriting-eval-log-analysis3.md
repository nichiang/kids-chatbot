# Prompt Metadata Logging Implementation Analysis

## Executive Summary

Analysis of how to add prompt metadata to individual LLM call logging without hardcoded mappings. The solution involves modifying existing prompt reading functions to capture and return metadata alongside the prompt content.

## Current Problem

Individual LLM call logging needs prompt metadata in this format:
```json
{
  "llm_calls": [
    {
      "type": "story_generation",
      "ai_output": "Max and Tink soared...",
      "prompt": {
        "file": "storywriting_prompts",
        "versions": "1.0.0", 
        "definition": "story_generation.story_opening.named_entities",
        "template_preview": "Create a story opening for the topic: {topic}..."
      },
      "duration": 3043.95
    }
  ]
}
```

Currently, this metadata is missing from individual LLM calls.

## Why We Can't Just Reuse `get_prompt_template()` Data

The user asked why we need to navigate the JSON again instead of using information from `get_prompt_template(category: str, key: str) -> str`.

**Answer:** We **should** reuse the navigation, but `get_prompt_template()` currently **discards** the metadata we need.

### Current Flow Analysis

When `get_prompt_template("story_templates", "named_entities")` is called:

1. **File Reading:** Function reads `storywriting-prompts.json`
2. **Navigation:** Navigates to `storywriting_prompts.story_generation.story_opening.named_entities`
3. **Metadata Access:** Has access to:
   - File name: "storywriting_prompts" 
   - Version: `metadata.version` ("1.0.0")
   - Definition path: "story_generation.story_opening.named_entities"
   - Template content: `prompt_template` field
4. **Data Loss:** Function only returns the `prompt_template` string, discarding all metadata

### The Issue

```python
# Current implementation - LOSES METADATA
def get_prompt_template(self, category: str, key: str) -> str:
    # Reads JSON, navigates to correct location
    storywriting_prompts = self.content.get("storywriting_prompts", {})
    story_generation = storywriting_prompts.get("story_generation", {})
    story_opening = story_generation.get("story_opening", {})
    template_data = story_opening.get(key, {})
    
    # ONLY returns the prompt - metadata is available but thrown away
    return template_data.get("prompt_template", template_data)
```

The function has access to all the metadata we need, but throws it away by only returning the prompt string.

## Solution Strategy

### Option 1: Modify Existing Function (Breaking Change)
Change `get_prompt_template()` to return both prompt and metadata:

```python
def get_prompt_template(self, category: str, key: str) -> dict:
    # Same navigation logic
    template_data = story_opening.get(key, {})
    
    return {
        "prompt": template_data.get("prompt_template", ""),
        "metadata": {
            "file": "storywriting_prompts",
            "versions": self.content.get("storywriting_prompts", {}).get("metadata", {}).get("version", "1.0.0"),
            "definition": "story_generation.story_opening.named_entities", 
            "template_preview": template_data.get("prompt_template", "")[:200]
        }
    }
```

**Problem:** This breaks all existing callers expecting a string.

### Option 2: Add New Function (Recommended)
Keep existing function, add metadata-aware version:

```python
def get_prompt_template_with_metadata(self, category: str, key: str) -> dict:
    # Reuse same navigation logic but capture metadata
    # Return both prompt and metadata
```

**Advantage:** Backward compatible, doesn't break existing code.

## Detailed Implementation Plan

### Phase 1: Add Metadata-Aware Function to ContentManager

**File:** `backend/content_manager.py`

**New Method:** `get_prompt_template_with_metadata(category: str, key: str) -> dict`

**Implementation Logic:**
1. **File Detection:** Determine source file from category
   - `"story_templates"` → `"storywriting_prompts"`
   - `"vocabulary_templates"` → `"shared_prompts"`
   
2. **Metadata Extraction:** When navigating JSON structure, capture:
   - **file:** Source file name (e.g., "storywriting_prompts")
   - **versions:** From `self.content[file]["metadata"]["version"]`
   - **definition:** JSON navigation path (e.g., "story_generation.story_opening.named_entities")
   - **template_preview:** First 200 chars of prompt_template

3. **Return Format:**
   ```python
   {
       "prompt": "actual prompt string",
       "metadata": {
           "file": "storywriting_prompts",
           "versions": "1.0.0",
           "definition": "story_generation.story_opening.named_entities",
           "template_preview": "Create a story opening for the topic: {topic}..."
       }
   }
   ```

### Phase 2: Update Prompt Manager Functions

**File:** `backend/prompt_manager.py`

**Target Functions:**
- `get_story_opening_prompt()`
- `get_story_ending_prompt()`
- `get_story_arc_assessment_prompt()`
- Any other functions that generate prompts for individual logging

**Changes:**
```python
def get_story_opening_prompt(self, topic: str, story_mode: str = "auto") -> tuple:
    # Current logic to determine template_key
    
    # Use new metadata-aware function
    template_with_metadata = content_manager.get_prompt_template_with_metadata("story_templates", template_key)
    
    formatted_prompt = template_with_metadata["prompt"].format(topic=topic)
    
    # Return both formatted prompt AND metadata
    return formatted_prompt, template_with_metadata["metadata"]
```

### Phase 3: Update LLM Call Chain

**File:** `backend/app.py`

**Target Locations:** All individual logging calls

**Pattern:**
```python
# OLD - only gets prompt
story_prompt = prompt_manager.get_story_opening_prompt(topic, "auto")
story_response = llm_provider.generate_response(story_prompt)
latency_logger.log_educational_interaction("story_generation", story_response, duration, educational_data)

# NEW - gets prompt + metadata  
story_prompt, prompt_metadata = prompt_manager.get_story_opening_prompt(topic, "auto")
story_response = llm_provider.generate_response(story_prompt)
latency_logger.log_educational_interaction("story_generation", story_response, duration, educational_data, prompt_metadata)
```

### Phase 4: Update All Individual Logging Calls

**Locations to Update:**
1. **Story Generation** (line 2231-2236)
2. **Story Assessment** (line 2590)
3. **Story Ending** (line 2618)
4. **Vocabulary Questions** (lines 2787, 2835, 2875, 2909)
5. **Grammar Feedback** (existing calls)

## TODO List

### **Phase 1: Core Infrastructure**
- [ ] Add `get_prompt_template_with_metadata()` method to `content_manager.py`
- [ ] Test metadata extraction for story templates
- [ ] Test metadata extraction for vocabulary templates
- [ ] Test metadata extraction for other template types

### **Phase 2: Prompt Manager Updates**
- [ ] Update `prompt_manager.get_story_opening_prompt()` to return metadata
- [ ] Update `prompt_manager.get_story_ending_prompt()` to return metadata  
- [ ] Update `prompt_manager.get_story_arc_assessment_prompt()` to return metadata
- [ ] Add any missing prompt manager functions for vocabulary/grammar

### **Phase 3: Individual Logging Updates**
- [ ] Update story generation logging (lines 2231-2236)
- [ ] Update story assessment logging (line 2590)
- [ ] Update story ending logging (line 2618)
- [ ] Update vocabulary question logging (4 locations)
- [ ] Update grammar feedback logging (existing calls)

### **Phase 4: Testing & Verification**
- [ ] Test story generation prompt metadata logging
- [ ] Test vocabulary question prompt metadata logging
- [ ] Test story assessment prompt metadata logging
- [ ] Test story ending prompt metadata logging
- [ ] Verify JSON output matches desired format
- [ ] Verify no hardcoded mappings remain

## Key Benefits

1. **No Hardcoded Mappings:** All metadata comes directly from JSON files
2. **Automatic Updates:** When JSON content changes, logging automatically reflects changes
3. **Backward Compatible:** Existing `get_prompt_template()` continues to work
4. **Single Source of Truth:** Metadata comes from same JSON navigation used for prompts

## Risk Mitigation

- **Comprehensive Error Handling:** Graceful fallbacks if metadata missing
- **Testing Strategy:** Test all prompt types and edge cases
- **Gradual Rollout:** Update one prompt type at a time
- **Monitoring:** Verify logging works correctly after each change

## Expected Outcome

Individual LLM call logging will include accurate, dynamically-sourced prompt metadata that automatically stays in sync with JSON file changes.