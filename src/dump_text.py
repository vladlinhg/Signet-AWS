import fitz
doc = fitz.open('/app/media/supporting_documents/test_344565.pdf')
text = ""
for page in doc:
    text += page.get_text("text") + "\n"

with open('/app/media/supporting_documents/dump.txt', 'w', encoding='utf-8') as f:
    f.write(text)
print("Dump successful!")
