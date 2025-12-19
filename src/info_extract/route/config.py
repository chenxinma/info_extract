# Create the API router
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import JSONResponse

from .tools import get_profile_manager
from ..config.profile_manager import ProfileManager
from ..config.config_models import Example, ExtractionAttribute, ExtractionRecord, InfoItem


config_router = APIRouter()

@config_router.get("/info_item", response_model=List[dict])
async def get_available_info_items(profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Get all available information items for the active profile to use for marking."""
    try:
        config_db = profile_manager.get_config_db()
        info_items = config_db.get_info_items()
        return [{
            'id': item.id,
            'label': item.label,
            'describe': item.describe,
            'data_type': item.data_type,
            'sort_no': item.sort_no,
            'sample_col_name': item.sample_col_name
        } for item in info_items]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@config_router.post('/info_item')
async def create_info_item(request: Request, profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Create a new info item in the database."""
    try:
        # Get the config_db instance from the profile manager to ensure we're using the active profile
        config_db = profile_manager.get_config_db()

        data = await request.json()
        # Add validation for required fields
        if not data.get('label') or not data.get('data_type'):
            return JSONResponse(content={'error': 'Label and data_type are required'}, status_code=400)

        # Use the ConfigDB method to create the item
        new_item = InfoItem(
            id=0,  # Will be set by the database
            label=data['label'],
            describe=data.get('describe'),
            data_type=data['data_type'],
            sort_no=data.get('sort_no'),
            sample_col_name=data.get('sample_col_name', ''),
            profile_id=profile_manager.get_current_profile_id()
        )

        # Return the created item with the new ID
        return {
            'id': config_db.add_item(new_item),
            'label': new_item.label,
            'describe': new_item.describe,
            'data_type': new_item.data_type,
            'sort_no': new_item.sort_no,
            'sample_col_name': new_item.sample_col_name
        }
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)


@config_router.put('/info_item/{item_id}')
async def update_info_item(item_id: int, request: Request, profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Update an existing info item in the database."""
    try:
        # Get the config_db instance from the profile manager to ensure we're using the active profile
        config_db = profile_manager.get_config_db()

        data = await request.json()
        # Add validation for required fields
        if not data.get('label') or not data.get('data_type'):
            return JSONResponse(content={'error': 'Label and data_type are required'}, status_code=400)

        rowcount = config_db.update_item(InfoItem(
            id = item_id,
            label = data['label'],
            describe = data.get('describe'),
            data_type = data['data_type'],
            sort_no = data.get('sort_no'),
            sample_col_name = data.get('sample_col_name', ''),
            profile_id=profile_manager.get_current_profile_id()
        ))
        if rowcount == 0:
            return JSONResponse(content={'error': 'Info item not found'}, status_code=404)

        # Return the updated item
        return {
            'id': item_id,
            'label': data['label'],
            'describe': data.get('describe'),
            'data_type': data['data_type'],
            'sort_no': data.get('sort_no'),
            'sample_col_name': data.get('sample_col_name', '')
        }
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)

@config_router.delete('/info_item/{item_id}')
async def delete_info_item(item_id: int, profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Delete an info item from the database."""
    try:
        # Get the config_db instance from the profile manager to ensure we're using the active profile
        config_db = profile_manager.get_config_db()

        rowcount = config_db.delete_item(item_id)

        if rowcount == 0:
            return JSONResponse(content={'error': 'Info item not found'}, status_code=404)

        return {'message': 'Info item deleted successfully'}
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)


# Route to handle sorting updates
@config_router.post('/info_item/sort')
async def update_sort_order(request: Request, profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Update the sort order of info items."""
    try:
        # Get the config_db instance from the profile manager to ensure we're using the active profile
        config_db = profile_manager.get_config_db()

        data = await request.json()
        item_orders = data.get('items', [])

        if not item_orders:
            return JSONResponse(content={'error': 'No items provided'}, status_code=400)

        config_db.update_items_sort(item_orders)

        return {'message': 'Sort order updated successfully'}
    except Exception as e:
        return JSONResponse(content={'error': str(e)}, status_code=500)


@config_router.get("/example", response_model=List[Example])
async def get_examples(profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Get all example texts for the active profile."""
    try:
        config_db = profile_manager.get_config_db()
        example_texts = config_db.get_examples()
        return example_texts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.get("/example/{example_id}", response_model=Example)
async def get_example_by_id(example_id: int, profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Get a specific example text by ID."""
    try:
        config_db = profile_manager.get_config_db()
        example_text = config_db.get_example_by_id(example_id)
        if not example_text:
            raise HTTPException(status_code=404, detail="Example text not found")
        return example_text
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.post("/example", response_model=Example)
async def create_example(fragment: str=Form(), profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Create a new example text."""
    try:
        config_db = profile_manager.get_config_db()
        example_id = config_db.create_example(fragment)
        
        # Retrieve and return the created example text
        created_example = config_db.get_example_by_id(example_id)
        if not created_example:
            raise HTTPException(status_code=500, detail="Failed to create example text")
        return created_example
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.put("/example/{example_id}", response_model=Example)
async def update_example(example_id: int, fragment: str=Form(), profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Update an existing example text."""
    try:
        config_db = profile_manager.get_config_db()
        result = config_db.update_example(example_id, fragment)
        if result == 0:
            raise HTTPException(status_code=404, detail="Example text not found")
        
        # Retrieve and return the updated example text
        updated_example = config_db.get_example_by_id(example_id)
        if not updated_example:
            raise HTTPException(status_code=500, detail="Failed to update example text")
        return updated_example
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.delete("/example/{example_id}")
async def delete_example(example_id: int, profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Delete an example text."""
    try:
        config_db = profile_manager.get_config_db()
        result = config_db.delete_example(example_id)
        if result == 0:
            raise HTTPException(status_code=404, detail="Example text not found")
        return {"message": "Example text deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.get("/example/{example_id}/extractions", response_model=List[ExtractionRecord])
async def get_all_extractions(example_id: Optional[int] = None, profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Get all extractions, optionally filtered by example text ID."""
    try:
        config_db = profile_manager.get_config_db()
        if example_id:
            extractions = config_db.get_extraction_records_by_example_id(example_id)
        else:
            # For this specific use case, we might want to implement a method to get all extractions
            # but for now, let's return extractions for a given example text ID only
            # If no example_text_id is provided, we can return an empty list
            extractions = []
            
        return extractions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.get("/extractions/{extraction_id}", response_model=ExtractionRecord)
async def get_extraction_by_id(extraction_id: int, profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Get a specific extraction record by ID."""
    try:
        config_db = profile_manager.get_config_db()
        extraction = config_db.get_extraction_record_by_id(extraction_id)
        if not extraction:
            raise HTTPException(status_code=404, detail="Extraction record not found")
        return extraction
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.post("/extractions", response_model=ExtractionRecord)
async def create_extraction_record(
    example_id: int=Form(), 
    extraction_info_item_id: int=Form(), 
    extraction_text: str=Form(), 
    profile_manager: ProfileManager = Depends(get_profile_manager)
):
    """Create a new extraction record."""
    try:
        config_db = profile_manager.get_config_db()
        extraction_id = config_db.create_extraction_record(example_id, extraction_info_item_id, extraction_text)
        
        # Retrieve and return the created extraction record
        created_extraction = config_db.get_extraction_record_by_id(extraction_id)
        if not created_extraction:
            raise HTTPException(status_code=500, detail="Failed to create extraction record")
        return created_extraction
    except Exception as e:
        profile_id=profile_manager.get_current_profile_id()
        raise HTTPException(status_code=500, detail=str(e))


@config_router.put("/extractions/{extraction_id}", response_model=ExtractionRecord)
async def update_extraction_record(extraction_id: int, 
                                   extraction_text: str=Form(), 
                                   profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Update an existing extraction record."""
    try:
        config_db = profile_manager.get_config_db()
        result = config_db.update_extraction_record(extraction_id, extraction_text)
        if result == 0:
            raise HTTPException(status_code=404, detail="Extraction record not found")
        
        # Retrieve and return the updated extraction record
        updated_extraction = config_db.get_extraction_record_by_id(extraction_id)
        if not updated_extraction:
            raise HTTPException(status_code=500, detail="Failed to update extraction record")
        return updated_extraction
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.delete("/extractions/{extraction_id}")
async def delete_extraction_record(extraction_id: int, profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Delete an extraction record."""
    try:
        config_db = profile_manager.get_config_db()
        result = config_db.delete_extraction_record(extraction_id)
        if result == 0:
            raise HTTPException(status_code=404, detail="Extraction record not found")
        return {"message": "Extraction record deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.get("/extractions/{extraction_id}/attributes", response_model=List[ExtractionAttribute])
async def get_extraction_attributes(extraction_id: int, profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Get all attributes for a specific extraction record."""
    try:
        config_db = profile_manager.get_config_db()
        attributes = config_db.get_extraction_attributes_by_extraction_id(extraction_id)
        return attributes
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.get("/extractions/attributes/{attribute_id}", response_model=ExtractionAttribute)
async def get_extraction_attribute_by_id(attribute_id: int, profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Get a specific extraction attribute by ID."""
    try:
        config_db = profile_manager.get_config_db()
        attribute = config_db.get_extraction_attribute_by_id(attribute_id)
        if not attribute:
            raise HTTPException(status_code=404, detail="Extraction attribute not found")
        return attribute
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.post("/extractions/{extraction_id}/attributes", response_model=ExtractionAttribute)
async def create_extraction_attribute(extraction_id: int, 
                                      key: str=Form(), 
                                      value: str=Form(), profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Create a new extraction attribute."""
    try:
        config_db = profile_manager.get_config_db()
        attribute_id = config_db.create_extraction_attribute(extraction_id, key, value)
        
        # Retrieve and return the created attribute
        created_attribute = config_db.get_extraction_attribute_by_id(attribute_id)
        if not created_attribute:
            raise HTTPException(status_code=500, detail="Failed to create extraction attribute")
        return created_attribute
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.put("/extractions/attributes/{attribute_id}", response_model=ExtractionAttribute)
async def update_extraction_attribute(attribute_id: int, 
                                      key: str=Form(), 
                                      value: str=Form(), 
                                      profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Update an existing extraction attribute."""
    try:
        config_db = profile_manager.get_config_db()
        result = config_db.update_extraction_attribute(attribute_id, key, value)
        if result == 0:
            raise HTTPException(status_code=404, detail="Extraction attribute not found")
        
        # Retrieve and return the updated attribute
        updated_attribute = config_db.get_extraction_attribute_by_id(attribute_id)
        if not updated_attribute:
            raise HTTPException(status_code=500, detail="Failed to update extraction attribute")
        return updated_attribute
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@config_router.delete("/extractions/attributes/{attribute_id}")
async def delete_extraction_attribute(attribute_id: int, 
                                      profile_manager: ProfileManager = Depends(get_profile_manager)):
    """Delete an extraction attribute."""
    try:
        config_db = profile_manager.get_config_db()
        result = config_db.delete_extraction_attribute(attribute_id)
        if result == 0:
            raise HTTPException(status_code=404, detail="Extraction attribute not found")
        return {"message": "Extraction attribute deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))






