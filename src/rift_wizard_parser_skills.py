import pandas as pd
import inspect
import importlib.util
import os

def load_module(filepath):
    """Load a Python module from file"""
    spec = importlib.util.spec_from_file_location("upgrades", filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def format_tags(tags):
    """Convert Tags objects into comma-separated string of school names"""
    if not tags:
        return ""
    try:
        tag_names = [tag.name for tag in tags]
        return ", ".join(tag_names)
    except AttributeError:
        return str(tags)

def format_tag_bonuses(tag_bonuses):
    """Format tag_bonuses dict into list of [tag, attribute, value] lists"""
    if not tag_bonuses:
        return []
    
    bonuses = []
    for tag, attrs in tag_bonuses.items():
        tag_name = tag.name if hasattr(tag, 'name') else str(tag)
        for attr, value in attrs.items():
            bonuses.append([tag_name, attr, value])
    return bonuses

def get_upgrade_attributes(upgrade_class):
    """Extract attributes from an upgrade class"""
    try:
        upgrade = upgrade_class()
    except TypeError:
        upgrade = upgrade_class
    except Exception as e:
        print(f"Could not instantiate {upgrade_class.__name__}: {e}")
        return None
    
    # Get description - can be either attribute or method
    if hasattr(upgrade, 'get_description') and callable(getattr(upgrade, 'get_description')):
        try:
            description = upgrade.get_description()
        except:
            description = getattr(upgrade, 'description', None)
    else:
        description = getattr(upgrade, 'description', None)

    # Check if required attributes exist
    name = getattr(upgrade, 'name', None)
    level = getattr(upgrade, 'level', None)
    tags = format_tags(getattr(upgrade, 'tags', []))

    # Get tag bonuses
    tag_bonuses = getattr(upgrade, 'tag_bonuses', {})
    bonuses = format_tag_bonuses(tag_bonuses)

    if not all([name, level is not None]):
        return None

    return {
        'name': name,
        'level': level,
        'tags': tags,
        'description': description,
        'bonuses': bonuses
    }

def is_upgrade_class(cls, module):
    """Check if a class is an upgrade class defined in the module"""
    try:
        if not inspect.isclass(cls):
            return False
        
        if cls.__module__ != module.__name__:
            return False
        
        if cls.__name__.endswith('Buff'):
            return False
        if cls.__name__.startswith('_'):
            return False
            
        obj = cls()
        
        return hasattr(obj, 'level') and hasattr(obj, 'name')
    except:
        return False

def create_upgrades_dataframe(filepath):
    # Load the upgrades module
    upgrades_module = load_module(filepath)
    
    # Get all upgrade classes from the module
    upgrade_classes = []
    for name, obj in inspect.getmembers(upgrades_module):
        if is_upgrade_class(obj, upgrades_module):
            upgrade_classes.append(obj)
    
    # Process each upgrade
    upgrade_data = []
    for cls in upgrade_classes:
        attrs = get_upgrade_attributes(cls)
        if attrs:  # Only include if we got valid attributes
            upgrade_data.append(attrs)
    
    if not upgrade_data:
        raise ValueError("No valid upgrades found")
    
    # Create DataFrame
    df = pd.DataFrame(upgrade_data)
    
    # Sort by level and name
    if not df.empty and 'level' in df.columns and 'name' in df.columns:
        df = df.sort_values(['level', 'name'])
    
    # Reorder columns
    column_order = ['name', 'tags', 'level', 'description', 'bonuses']
    df = df[column_order]
    
    return df

# Example usage
if __name__ == "__main__":
    upgrades_file = "Upgrades.py"
    
    if not os.path.exists(upgrades_file):
        print(f"Error: {upgrades_file} not found")
        exit(1)
    
    try:
        upgrades_df = create_upgrades_dataframe(upgrades_file)
        
        # Print summary info
        print(f"\nTotal upgrades: {len(upgrades_df)}")
        print("\nUpgrades by level:")
        print(upgrades_df['level'].value_counts().sort_index())
        
        # Save to CSV
        upgrades_df.to_csv('upgrades_analysis.csv', index=False)
        
        # Print sample
        if not upgrades_df.empty:
            print("\nSample upgrade with bonuses:")
            sample = upgrades_df[upgrades_df['bonuses'].str.len() > 0].iloc[0]
            print(f"Name: {sample['name']}")
            print(f"Tags: {sample['tags']}")
            print(f"Level: {sample['level']}")
            print("Tag Bonuses:")
            for bonus in sample['bonuses']:
                print(f"  {bonus[0]} {bonus[1]}: {bonus[2]}")
            
    except Exception as e:
        print(f"Error creating upgrades dataframe: {e}")
        raise