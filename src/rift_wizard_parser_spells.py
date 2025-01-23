# https://docs.google.com/spreadsheets/d/138efPbH7AgsARwiemFfd1euvw9f-m8E1g1F4KFHgDLc/edit?gid=2025145576#gid=2025145576

import pandas as pd
import inspect
import importlib.util
import os

def load_spells_module(filepath):
    """Load the Spells.py module from file"""
    spec = importlib.util.spec_from_file_location("spells", filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def get_spell_attributes(spell_class):
    # Create instance of spell
    spell = spell_class()
    
    # Get base attributes
    base_attrs = {
        'name': getattr(spell, 'name', None),
        'level': getattr(spell, 'level', None),
        'max_charges': getattr(spell, 'max_charges', None),
        'range': getattr(spell, 'range', None),
        'tags': ','.join([str(t) for t in getattr(spell, 'tags', [])]),
        'damage': getattr(spell, 'damage', None),
        'duration': getattr(spell, 'duration', None),
        'radius': getattr(spell, 'radius', None),
        'num_targets': getattr(spell, 'num_targets', None)
    }
    
    # Get upgrades
    upgrades = getattr(spell, 'upgrades', {})
    upgrade_attrs = {}
    
    for upgrade_name, upgrade_data in upgrades.items():
        if isinstance(upgrade_data, tuple):
            # Handle numeric upgrades
            if len(upgrade_data) >= 2:
                upgrade_attrs[f'upgrade_{upgrade_name}_value'] = upgrade_data[0]
                upgrade_attrs[f'upgrade_{upgrade_name}_cost'] = upgrade_data[1]
            # Handle named upgrades
            if len(upgrade_data) >= 4:
                upgrade_attrs[f'upgrade_{upgrade_name}_name'] = upgrade_data[2]
                upgrade_attrs[f'upgrade_{upgrade_name}_desc'] = upgrade_data[3]
    
    # Combine base attributes and upgrades
    return {**base_attrs, **upgrade_attrs}

def create_spells_dataframe(filepath):
    # Load the spells module
    spells_module = load_spells_module(filepath)
    
    # Get the Spell base class
    Spell = getattr(spells_module, 'Spell')
    
    # Get all spell classes from the module
    spell_classes = [obj for name, obj in inspect.getmembers(spells_module) 
                    if inspect.isclass(obj) and issubclass(obj, Spell) and obj != Spell]
    
    # Convert each spell class to a dictionary of attributes
    spell_data = [get_spell_attributes(cls) for cls in spell_classes]
    
    # Create DataFrame
    df = pd.DataFrame(spell_data)
    
    # Sort by level and name
    df = df.sort_values(['level', 'name'])
    
    return df

# Usage example:
if __name__ == "__main__":
    # Specify path to Spells.py
    
    # cd "G:\SteamLibrary\steamapps\common\Rift Wizard\RiftWizard"
    
    spells_file = "Spells.py"
    
    if not os.path.exists(spells_file):
        print(f"Error: {spells_file} not found")
        exit(1)
        
    # Create the dataframe
    spells_df = create_spells_dataframe(spells_file)
    
    # Print basic info
    print(f"Total spells: {len(spells_df)}")
    print("\nColumns:")
    for col in spells_df.columns:
        print(col)
        
    # Example analysis
    print("\nSpells by level:")
    print(spells_df['level'].value_counts().sort_index())
    
    # Optionally save to CSV
    spells_df.to_csv('spells_analysis.csv', index=False)
