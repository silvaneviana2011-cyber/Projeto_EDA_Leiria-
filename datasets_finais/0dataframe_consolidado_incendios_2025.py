# -*- coding: utf-8 -*-
"""
DataFrame consolidado para analise exploratoria de incendios florestais.

Objetivo:
Integrar temperatura, PDSI, area ardida e numero de incendios
para municipios da regiao de Leiria e municipios adjacentes.

Periodo analisado: maio a outubro de 2025.
"""

import struct
import unicodedata

import pandas as pd


# =========================
# 1. CAMINHOS DOS FICHEIROS
# =========================

pasta = r"C:\Users\silva\Desktop\EDA_prof_Albano_projeto"

ficheiro_temperatura = pasta + r"\temp_max_2025-leiria.csv"
ficheiro_pdsi = pasta + r"\mpdsi-per_seca1009-leiria.csv"
ficheiro_area_ardida = pasta + r"\ardida_2025.dbf"


# =========================
# 2. PARAMETROS DA ANALISE
# =========================

ano_analise = 2025
mes_inicio = 5
mes_fim = 10

municipios_analise = [
    "Leiria",
    "Pombal",
    "Marinha Grande",
    "Alcobaca",
    "Nazare",
    "Porto de Mos",
    "Batalha",
    "Ourem",
    "Ansiao"
]


# =========================
# 3. FUNCOES AUXILIARES
# =========================

def ler_dbf(caminho):
    """
    Le ficheiros DBF sem depender de bibliotecas externas.
    Devolve uma tabela pandas com os atributos do shapefile.
    """
    with open(caminho, "rb") as f:
        cabecalho = f.read(32)
        numero_registos = struct.unpack("<I", cabecalho[4:8])[0]
        tamanho_cabecalho = struct.unpack("<H", cabecalho[8:10])[0]
        tamanho_registo = struct.unpack("<H", cabecalho[10:12])[0]

        campos = []

        while True:
            descritor = f.read(32)

            if descritor[0] == 0x0D:
                break

            nome = descritor[:11].split(b"\x00", 1)[0].decode("latin1")
            tamanho = descritor[16]
            campos.append((nome, tamanho))

        f.seek(tamanho_cabecalho)

        linhas = []

        for _ in range(numero_registos):
            registo = f.read(tamanho_registo)

            if not registo or registo[0:1] == b"*":
                continue

            posicao = 1
            linha = {}

            for nome, tamanho in campos:
                valor = registo[posicao:posicao + tamanho]
                posicao += tamanho
                valor = valor.decode("latin1", errors="ignore").strip()
                linha[nome] = valor

            linhas.append(linha)

    return pd.DataFrame(linhas)


def normalizar_texto(valor):
    """
    Remove acentos e espacos extra para permitir comparacoes consistentes.
    Exemplo: 'Porto de Mos' e 'Porto de Mós' passam a ser comparaveis.
    """
    if pd.isna(valor):
        return ""

    texto = str(valor).strip()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto


# =========================
# 4. TEMPERATURA MEDIA MENSAL
# =========================

temperatura = pd.read_csv(ficheiro_temperatura)

temperatura["date"] = pd.to_datetime(
    temperatura["date"],
    errors="coerce"
)

temperatura["mean"] = pd.to_numeric(
    temperatura["mean"],
    errors="coerce"
)

temperatura = temperatura[
    (temperatura["date"].dt.year == ano_analise) &
    (temperatura["date"].dt.month >= mes_inicio) &
    (temperatura["date"].dt.month <= mes_fim)
].copy()

temperatura["mes"] = temperatura["date"].dt.month

temperatura_mensal = (
    temperatura
    .groupby("mes", as_index=False)
    .agg(temperatura_media=("mean", "mean"))
)


# =========================
# 5. PDSI MENSAL
# =========================

pdsi = pd.read_csv(ficheiro_pdsi)

pdsi["date"] = pd.to_datetime(
    pdsi["date"],
    errors="coerce"
)

pdsi["mean"] = pd.to_numeric(
    pdsi["mean"],
    errors="coerce"
)

pdsi = pdsi[
    (pdsi["date"].dt.year == ano_analise) &
    (pdsi["date"].dt.month >= mes_inicio) &
    (pdsi["date"].dt.month <= mes_fim)
].copy()

pdsi["mes"] = pdsi["date"].dt.month

pdsi_mensal = (
    pdsi
    .groupby("mes", as_index=False)
    .agg(pdsi=("mean", "mean"))
)


# =========================
# 6. AREA ARDIDA E INCENDIOS
# =========================

area_ardida = ler_dbf(ficheiro_area_ardida)

area_ardida["DH_Inicio"] = pd.to_datetime(
    area_ardida["DH_Inicio"],
    format="%Y%m%d",
    errors="coerce"
)

area_ardida["AreaHaSIG"] = pd.to_numeric(
    area_ardida["AreaHaSIG"],
    errors="coerce"
)

area_ardida["municipio_norm"] = area_ardida["PI_Conc"].apply(normalizar_texto)
area_ardida["ano"] = area_ardida["DH_Inicio"].dt.year
area_ardida["mes"] = area_ardida["DH_Inicio"].dt.month

municipios_norm = [normalizar_texto(municipio) for municipio in municipios_analise]

area_ardida_filtrada = area_ardida[
    (area_ardida["ano"] == ano_analise) &
    (area_ardida["mes"] >= mes_inicio) &
    (area_ardida["mes"] <= mes_fim) &
    (area_ardida["municipio_norm"].isin(municipios_norm))
].copy()

area_incendios_mensal = (
    area_ardida_filtrada
    .groupby("mes", as_index=False)
    .agg(
        area_ardida_mensal=("AreaHaSIG", "sum"),
        numero_incendios_mensal=("Cod_SGIF", "count")
    )
)


# =========================
# 7. DATAFRAME CONSOLIDADO
# =========================

dataframe_consolidado = pd.DataFrame({
    "mes": list(range(mes_inicio, mes_fim + 1))
})

dataframe_consolidado = dataframe_consolidado.merge(
    temperatura_mensal,
    on="mes",
    how="left"
)

dataframe_consolidado = dataframe_consolidado.merge(
    pdsi_mensal,
    on="mes",
    how="left"
)

dataframe_consolidado = dataframe_consolidado.merge(
    area_incendios_mensal,
    on="mes",
    how="left"
)


# =========================
# 8. TRATAMENTO DE VALORES NULOS
# =========================

# Se nao houve incendios num mes, a area ardida e o numero de incendios sao zero.
dataframe_consolidado["area_ardida_mensal"] = (
    dataframe_consolidado["area_ardida_mensal"]
    .fillna(0)
)

dataframe_consolidado["numero_incendios_mensal"] = (
    dataframe_consolidado["numero_incendios_mensal"]
    .fillna(0)
    .astype(int)
)

# Temperatura e PDSI podem ficar nulos caso nao existam dados climaticos no mes.
# Para permitir heatmap de correlacao sem erros, os nulos sao preenchidos pela media.
dataframe_consolidado["temperatura_media"] = (
    dataframe_consolidado["temperatura_media"]
    .fillna(dataframe_consolidado["temperatura_media"].mean())
)

dataframe_consolidado["pdsi"] = (
    dataframe_consolidado["pdsi"]
    .fillna(dataframe_consolidado["pdsi"].mean())
)


# =========================
# 9. GARANTIR COMPATIBILIDADE COM HEATMAP
# =========================

colunas_finais = [
    "mes",
    "temperatura_media",
    "pdsi",
    "area_ardida_mensal",
    "numero_incendios_mensal"
]

dataframe_consolidado = dataframe_consolidado[colunas_finais]

for coluna in colunas_finais:
    dataframe_consolidado[coluna] = pd.to_numeric(
        dataframe_consolidado[coluna],
        errors="coerce"
    )

dataframe_consolidado = dataframe_consolidado.fillna(0)


# =========================
# 10. RESULTADOS
# =========================

print("===== DataFrame consolidado - Maio a Outubro de 2025 =====")
print(dataframe_consolidado)

print("\n===== Verificacao de valores nulos =====")
print(dataframe_consolidado.isna().sum())

print("\n===== Matriz de correlacao para heatmap =====")
matriz_correlacao = dataframe_consolidado.corr(numeric_only=True)
print(matriz_correlacao)
