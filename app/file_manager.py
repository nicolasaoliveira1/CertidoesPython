import os
import shutil
import time
import glob
from thefuzz import process

# CONFIGURAÇÕES
CAMINHO_REDE = r"Z:\PASTAS EMPRESAS"
VARIACOES_DOCS = [
    "DOCUMENTOS EMPRESA", "DOCS. EMPRESA", "DOC. EMPRESA", 
    "DOCUMENTOS", "DOCS", "DOCS EMPRESA", "DOC EMPRESA"
]

def encontrar_pasta_empresa(nome_banco):
    """
    Procura a pasta da empresa no servidor usando correspondência aproximada (Fuzzy).
    """
    if not os.path.exists(CAMINHO_REDE):
        print(f"ERRO: Caminho de rede não encontrado: {CAMINHO_REDE}")
        return None

    try:
        todas_pastas = os.listdir(CAMINHO_REDE)
        resultado = process.extractOne(nome_banco, todas_pastas, score_cutoff=85)
        
        if resultado:
            pasta_encontrada = resultado[0]
            print(f"Pasta encontrada para '{nome_banco}': {pasta_encontrada}")
            return os.path.join(CAMINHO_REDE, pasta_encontrada)
        else:
            print(f"Nenhuma pasta encontrada para: {nome_banco}")
            return None
    except Exception as e:
        print(f"Erro ao buscar pasta: {e}")
        return None

def encontrar_caminho_final(caminho_empresa):
    """
    Dentro da pasta da empresa, procura onde salvar as certidões.
    """
    pasta_destino = caminho_empresa
    
    for variacao in VARIACOES_DOCS:
        teste_path = os.path.join(caminho_empresa, variacao)
        if os.path.exists(teste_path):
            pasta_destino = teste_path
            break
    
    pasta_certidoes = os.path.join(pasta_destino, "CERTIDOES")
    if not os.path.exists(pasta_certidoes):
        try:
            os.makedirs(pasta_certidoes)
            print(f"Pasta CERTIDOES criada em: {pasta_certidoes}")
        except OSError:
            print("Erro ao criar pasta CERTIDOES, usando raiz.")
            return pasta_destino

    return pasta_certidoes

def verificar_novo_arquivo(tempo_inicio):
    """
    Verifica se apareceu um arquivo novo na pasta Downloads do usuário.
    """
    pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    padrao_busca = os.path.join(pasta_downloads, "*")
    
    arquivos = glob.glob(padrao_busca)
    arquivos = [f for f in arquivos if os.path.isfile(f)]
    
    if not arquivos:
        return None

    arquivo_mais_recente = max(arquivos, key=os.path.getctime)
    tempo_criacao = os.path.getctime(arquivo_mais_recente)
    
    if tempo_criacao > tempo_inicio:
        if not arquivo_mais_recente.endswith('.crdownload') and not arquivo_mais_recente.endswith('.tmp'):
            return arquivo_mais_recente
            
    return None

def mover_e_renomear(caminho_arquivo_origem, nome_empresa, tipo_certidao):
    """
    Move o arquivo baixado para o servidor com o nome correto.
    """
    caminho_empresa = encontrar_pasta_empresa(nome_empresa)
    
    if not caminho_empresa:
        return False, "Pasta da empresa não encontrada no Z:"

    destino_final = encontrar_caminho_final(caminho_empresa)
    
    extensao = os.path.splitext(caminho_arquivo_origem)[1]
    novo_nome = f"CERTIDAO {tipo_certidao.upper()}{extensao}"
    
    caminho_destino_completo = os.path.join(destino_final, novo_nome)
    
    try:
        shutil.move(caminho_arquivo_origem, caminho_destino_completo)
        print(f"Arquivo movido com sucesso para: {caminho_destino_completo}")
        return True, caminho_destino_completo
    except Exception as e:
        print(f"Erro ao mover arquivo: {e}")
        return False, str(e)