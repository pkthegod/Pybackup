import PyPDF2
import re
from tabulate import tabulate
import pandas as pd

jvmPath = r"C:\Program Files\Java\jdk-17\bin\server\jvm.dll"

pdf_file = open(r"C:\bloqueio26.pdf", 'rb')

pdf = PyPDF2.PdfReader(pdf_file)

tabelaComum = tabulate.read_pdf(r"C:\bloqueio26.pdf", pages="all")
for tabela in tabelaComum:
    play(tabela)

pdf_file.close()