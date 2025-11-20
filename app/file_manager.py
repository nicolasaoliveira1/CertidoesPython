import os
import shutil
import time
import glob
import unicodedata
from thefuzz import process, fuzz

CAMINHO_REDE = r"Z:\PASTAS EMPRESAS"
VARIACOES_DOCS = [
    "DOCUMENTOS EMPRESA", "DOCS. EMPRESA", "DOC. EMPRESA", 
    "DOCUMENTOS", "DOCS", "DOCS EMPRESA", "DOC EMPRESA"
]
STOP_FEDERAL_KEY = 'stop_federal_monitor.txt'

def obter_caminho_chave_interrupcao():
    """Retorna o caminho completo para o arquivo de interrupção."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), STOP_FEDERAL_KEY)

def criar_chave_interrupcao():
    """Cria o arquivo de interrupção."""
    caminho_chave = obter_caminho_chave_interrupcao()
    with open(caminho_chave, 'w') as f:
        f.write(str(time.time()))
    print(f"Chave de interrupção criada em: {caminho_chave}")
    
def remover_chave_interrupcao():
    """Remove o arquivo de interrupção."""
    caminho_chave = obter_caminho_chave_interrupcao()
    if os.path.exists(caminho_chave):
        os.remove(caminho_chave)
        print("Chave de interrupção removida.")
        
def remover_acentos(texto):
    if not texto:
        return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')

def encontrar_pasta_empresa(nome_banco):
    if not os.path.exists(CAMINHO_REDE):
        print(f"ERRO: Caminho de rede não encontrado: {CAMINHO_REDE}")
        return None

    try:
        todas_pastas_brutas = os.listdir(CAMINHO_REDE)
        
        todas_pastas = [
            pasta for pasta in todas_pastas_brutas 
            if "FILIAL" not in pasta.upper()
        ]
        
        resultado = process.extractOne(nome_banco, todas_pastas, score_cutoff=95)
        
        if resultado:
            pasta_encontrada = resultado[0]
            print(f"Pasta encontrada (Match Direto): '{pasta_encontrada}'")
            return os.path.join(CAMINHO_REDE, pasta_encontrada)
        
        resultado_token = process.extractOne(nome_banco, todas_pastas, scorer=fuzz.token_set_ratio, score_cutoff=100)
        
        if resultado_token:
            pasta_encontrada = resultado_token[0]
            print(f"Pasta encontrada (Match Inteligente): '{pasta_encontrada}'")
            return os.path.join(CAMINHO_REDE, pasta_encontrada)

        nome_banco_clean = remover_acentos(nome_banco).upper()
        
        for pasta in todas_pastas:
            pasta_clean = remover_acentos(pasta).upper()
            
            score = fuzz.token_set_ratio(nome_banco_clean, pasta_clean)
            
            if score == 100:
                print(f"Pasta encontrada (Match Sem Acentos): '{pasta}'")
                return os.path.join(CAMINHO_REDE, pasta)

        for pasta in todas_pastas:
            if pasta.upper() == nome_banco.upper():
                print(f"Pasta encontrada (Match Exato): '{pasta}'")
                return os.path.join(CAMINHO_REDE, pasta)

        print(f"ALERTA DE SEGURANÇA: Nenhuma pasta confiável encontrada para: '{nome_banco}'")
        print("O arquivo permanecerá na pasta Downloads para evitar erros.")
        return None
            
    except Exception as e:
        print(f"Erro ao buscar pasta: {e}")
        return None
    
def encontrar_caminho_final(caminho_empresa):
    
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
        except OSError:
            return pasta_destino

    return pasta_certidoes

def limpar_versoes_antigas(pasta_destino, novo_nome_padrao, tipo_certidao):
    try:
        arquivos_existentes = os.listdir(pasta_destino)
        palavra_chave = tipo_certidao.upper()
        
        for arquivo in arquivos_existentes:
            caminho_completo = os.path.join(pasta_destino, arquivo)
            
            if not os.path.isfile(caminho_completo):
                continue
                
            if arquivo.upper() == novo_nome_padrao.upper():
                continue

            if arquivo.lower().endswith('.pdf'):
                semelhanca = fuzz.partial_ratio(palavra_chave, arquivo.upper())
                
                if semelhanca > 85:
                    print(f"Removendo arquivo antigo/fora do padrão: {arquivo}")
                    os.remove(caminho_completo)
                    
    except Exception as e:
        print(f"Erro ao tentar limpar versões antigas: {e}")

def verificar_novo_arquivo(tempo_inicio, termos_ignorar=None):
    pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    padrao_busca = os.path.join(pasta_downloads, "*")
    
    arquivos = glob.glob(padrao_busca)
    arquivos = [f for f in arquivos if os.path.isfile(f)]
    
    if not arquivos:
        return None

    arquivo_mais_recente = max(arquivos, key=os.path.getctime)
    tempo_criacao = os.path.getctime(arquivo_mais_recente)
    
    # Debug: Vamos ver o que ele encontrou
    nome_arquivo = os.path.basename(arquivo_mais_recente).lower()
    
    if tempo_criacao > tempo_inicio:
        # Debug
        print(f"[DEBUG] Arquivo novo encontrado: {nome_arquivo}")

        if nome_arquivo.endswith('.crdownload') or nome_arquivo.endswith('.tmp'):
            # Debug
            print(f"[DEBUG] Ignorado pois é temporário: {nome_arquivo}")
            return None

        if termos_ignorar:
            for termo in termos_ignorar:
                if termo.lower() in nome_arquivo:
                    print(f"Arquivo ignorado pelo filtro '{termo}': {nome_arquivo}")
                    return None

        print(f"[SUCESSO] Arquivo aceito: {nome_arquivo}")
        return arquivo_mais_recente
            
    return None

def mover_e_renomear(caminho_arquivo_origem, nome_empresa, tipo_certidao):
    caminho_empresa = encontrar_pasta_empresa(nome_empresa)
    
    if not caminho_empresa:
        return False, "Pasta da empresa não encontrada no Z:"

    destino_final = encontrar_caminho_final(caminho_empresa)
    
    extensao = os.path.splitext(caminho_arquivo_origem)[1]
    novo_nome = f"CERTIDAO {tipo_certidao.upper()}{extensao}"

    limpar_versoes_antigas(destino_final, novo_nome, tipo_certidao)

    
    caminho_destino_completo = os.path.join(destino_final, novo_nome)
    
    try:
        shutil.move(caminho_arquivo_origem, caminho_destino_completo)
        return True, caminho_destino_completo
    except Exception as e:
        try:
            shutil.copy2(caminho_arquivo_origem, caminho_destino_completo)
            os.remove(caminho_arquivo_origem)
            return True, caminho_destino_completo
        except Exception as e2:
            return False, str(e2)