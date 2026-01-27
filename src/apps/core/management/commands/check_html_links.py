from django.core.management.base import BaseCommand
from django.template.loader import get_template
from django.template import Context, Template
from django.conf import settings
from django.urls import reverse, NoReverseMatch
import os
import re

class Command(BaseCommand):
    help = 'Scans templates for broken URL lookups.'

    def handle(self, *args, **options):
        template_dir = settings.BASE_DIR / 'templates'
        errors = []
        checked_count = 0
        
        # Regex to find {% url 'name' ... %}
        # Checking for both single and double quotes
        url_pattern = re.compile(r"{%\s*url\s+['\"]([\w:_-]+)['\"]\s*.*?%}")

        for root, dirs, files in os.walk(template_dir):
            for file in files:
                if file.endswith('.html'):
                    path = os.path.join(root, file)
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    matches = url_pattern.findall(content)
                    for url_name in matches:
                        checked_count += 1
                        try:
                            # We can't easily resolve URLs with arguments without dummy data.
                            # But we CAN verify the *name* exists in the registry.
                            # However, reverse() throws NoReverseMatch if args missing.
                            # So this check is limited to "Is the name valid?" if we can query the resolver.
                            # Actually, get_resolver().reverse_dict is internal.
                            # A better minimal check: 
                            pass 
                        except Exception:
                            pass
        
        # Since resolving with args is hard statically, we will iterate over urlconf to see if the name is known.
        # This is a bit complex for a regex scan.
        # Alternative: Just report what we found for now?
        # User asked to "Report any potential 404".
        
        # Let's try to verify against the URL resolver's known names.
        from django.urls import get_resolver
        resolver = get_resolver()
        
        def extract_names(urlpatterns, parent=''):
            names = set()
            for pattern in urlpatterns:
                if hasattr(pattern, 'url_patterns'):
                    # Include
                    # Check if namespace
                    prefix = parent
                    if hasattr(pattern, 'namespace') and pattern.namespace:
                        prefix = f"{parent}{pattern.namespace}:"
                    names.update(extract_names(pattern.url_patterns, prefix))
                elif hasattr(pattern, 'name') and pattern.name:
                    names.add(f"{parent}{pattern.name}")
            return names

        known_names = extract_names(resolver.url_patterns)
        # Add admin names manually or recursively? Admin urls are included.
        # Admin usually has 'admin:index', 'admin:app_model_change', etc.
        # The recursion should catch 'admin:index' if includes work.
        
        for root, dirs, files in os.walk(template_dir):
             for file in files:
                if file.endswith('.html'):
                    path = os.path.join(root, file)
                    rel_path = os.path.relpath(path, template_dir)
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    matches = url_pattern.findall(content)
                    for url_name in matches:
                        # Skip variable urls
                        if ' ' in url_name: continue
                        
                        # Handle 'admin:...'
                        # Our recursive extractor might miss deep dynamic admin urls.
                        if url_name.startswith('admin:'): continue 
                        
                        if url_name not in known_names:
                            # Try adding to list of suspect
                            errors.append(f"[{rel_path}] Unknown URL name: '{url_name}'")

        if errors:
            self.stdout.write(self.style.ERROR(f"Found {len(errors)} potential broken links:"))
            for e in errors:
                self.stdout.write(e)
            self.stdout.write(self.style.WARNING("Note: Admin URLs and dynamic names skipped."))
        else:
            self.stdout.write(self.style.SUCCESS("No obvious broken URL names found."))
