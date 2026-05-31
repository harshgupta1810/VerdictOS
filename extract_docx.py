import docx
doc = docx.Document('VerdictOS System Architecture Report.docx')
with open('docx_output3.txt', 'w', encoding='utf-8') as f:
    for p in doc.paragraphs:
        f.write(p.text + '\n')
