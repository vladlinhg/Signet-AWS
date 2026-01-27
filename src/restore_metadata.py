import os

apps_data = {
    'apps/invoices': 'InvoicesConfig',
    'apps/clients': 'ClientsConfig',
    'apps/flights': 'FlightsConfig',
    'apps/tours': 'ToursConfig',
    'apps/currencies': 'CurrenciesConfig',
    'engine/records/invoices': None,
    'engine/records/clients': None,
    'engine/records/flights': None,
    'engine/records/tours': None,
    'engine/records/currencies': None,
    'engine/pages/sales': 'SalesConfig',
    'engine/pages/manager': 'ManagerConfig',
    'engine/pages/accountant': 'AccountantConfig',
    'engine/pages/marketing': 'MarketingConfig'
}

# The user might have marketing in engine/pages/marketing (dot path vs path)
# Correcting 'engine.pages/marketing' key to 'engine/pages/marketing'
# apps_data['engine/pages/marketing'] = 'MarketingConfig' # Fixed in dict above

base = 'd:/Signet/src'

for path, config_class in apps_data.items():
    if '.' in path and not '/' in path: path = path.replace('.', '/') # Minimal fix
    
    full_path = os.path.join(base, path)
    if not os.path.exists(full_path):
        os.makedirs(full_path, exist_ok=True)
    
    # Init File
    init_f = os.path.join(full_path, '__init__.py')
    if os.path.exists(init_f):
        try:
            os.remove(init_f)
        except PermissionError:
            print(f"Skipping locked file: {init_f}")
            
    with open(init_f, 'w', encoding='utf-8') as f:
        f.write('# Init\n')
        
    # Apps File
    if config_class:
        apps_f = os.path.join(full_path, 'apps.py')
        if os.path.exists(apps_f):
            try:
                os.remove(apps_f)
            except:
                pass
            
        # Determine label/name
        # name is the dot path: apps.invoices
        name = path.replace('/', '.')
        label = path.split('/')[-1]
        
        content = f"from django.apps import AppConfig\n\nclass {config_class}(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = '{name}'\n    label = '{label}'\n"
        
        with open(apps_f, 'w', encoding='utf-8') as f:
            f.write(content)

print('Restored metadata files.')
