from django import forms

class ImportDataForm(forms.Form):
    TYPE_CHOICES = [
        ('clients', 'Clients CSV'),
        ('flights', 'Flights CSV'),
        ('tours', 'Tours/Products CSV'),
        ('users', 'Users CSV'),
        ('currencies', 'Currencies CSV'),
    ]
    import_type = forms.ChoiceField(choices=TYPE_CHOICES, label="Data Type")
    file = forms.FileField(label="Select CSV File", help_text="Upload a .csv file")

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name.endswith('.csv'):
            raise forms.ValidationError("Only .csv files are allowed.")
        return file
    
class WipeDataForm(forms.Form):
    confirm_string = forms.CharField(
        label="CONFIRMATION",
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'DELETE-ALL-DATA', 'class': 'border p-2 w-full'})
    )
    manager_code = forms.CharField(
        label="Manager Approval Code",
        max_length=50,
        widget=forms.PasswordInput(attrs={'class': 'border p-2 w-full', 'placeholder': 'Ask your Manager'})
    )

    def clean(self):
        cleaned_data = super().clean()
        confirm = cleaned_data.get("confirm_string")
        code = cleaned_data.get("manager_code")

        if confirm != "DELETE-ALL-DATA":
            self.add_error('confirm_string', "Incorrect confirmation string.")
        
        # Hardcoded approval code for demo
        if code != "MGR-APPROVE":
            self.add_error('manager_code', "Invalid Manager Approval Code.")
