import PyPDF2
import re
import tabula

jvmPath = r"C:\Program Files\Java\jdk-17\bin\server\jvm.dll"

pdf_file = open(r"C:\bloqueio26.pdf", 'rb')

pdf = PyPDF2.PdfReader(pdf_file)

tabelaComum = tabula.read_pdf(r"C:\bloqueio26.pdf", pages="all")
for tabela in tabelaComum:
    display(tabela)

pdf_file.close()