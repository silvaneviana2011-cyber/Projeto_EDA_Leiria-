# -*- coding: utf-8 -*-
"""
Created on Thu May 21 11:10:43 2026

@author: silva
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

# Dados da tabela
dados = {
    "Mês": ["Maio", "Junho", "Julho"],
    "Temperatura": [21.3, 24.1, 32.9],
    "Área Ardida": [1.8, 5.8, 14.2],
    "Incêndios": [1, 5, 7]
}

df = pd.DataFrame(dados)

# Caminho de saída
pasta_saida = r"C:\Users\silva\Desktop\EDA_prof_Albano_projeto\graficos"
nome_ficheiro = "tabela_indicadores.png"
caminho_png = os.path.join(pasta_saida, nome_ficheiro)

# Criar a pasta caso ela não exista
os.makedirs(pasta_saida, exist_ok=True)

# Criar figura
fig, ax = plt.subplots(figsize=(10, 3.5))
ax.axis("off")

# Criar tabela
tabela = ax.table(
    cellText=df.values,
    colLabels=df.columns,
    cellLoc="center",
    loc="center"
)

# Estilo da tabela
tabela.auto_set_font_size(False)
tabela.set_fontsize(12)
tabela.scale(1.2, 1.8)

cor_cabecalho = "#1F4E78"
cor_linha_par = "#D9EAF7"
cor_linha_impar = "#FFFFFF"
cor_borda = "#A6A6A6"

for (linha, coluna), celula in tabela.get_celld().items():
    celula.set_edgecolor(cor_borda)
    celula.set_linewidth(1)

    if linha == 0:
        celula.set_facecolor(cor_cabecalho)
        celula.set_text_props(color="white", weight="bold")
    else:
        if linha % 2 == 0:
            celula.set_facecolor(cor_linha_par)
        else:
            celula.set_facecolor(cor_linha_impar)

# Título
plt.title(
    "Tabela de Indicadores - Maio a Julho 2025",
    fontsize=14,
    fontweight="bold",
    pad=20
)

# Guardar em PNG
fig.savefig(
    caminho_png,
    dpi=300,
    bbox_inches="tight"
)

# Mostrar no Spyder
plt.show()

print("PNG guardado com sucesso em:")
print(caminho_png)