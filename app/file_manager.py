import os
import shutil
import time
import glob
import unicodedata
from thefuzz import process, fuzz

CAMINHO_REDE = r"Z:\PASTAS EMPRESAS"
CAMINHO_SEM_MOVIMENTO = os.path.join(
    CAMINHO_REDE, "A a Z", "EMPRESAS SEM MOVIMENTO")
VARIACOES_DOCS = [
    "DOCUMENTOS EMPRESA", "DOCS. EMPRESA", "DOC. EMPRESA",
    "DOCUMENTOS", "DOCS", "DOCS EMPRESA", "DOC EMPRESA", 
    "DOCUMENTO EMPRESA"
]
STOP_FEDERAL_KEY = 'stop_federal_monitor.txt'


def obter_caminho_chave_interrupcao():
    """Retorna o caminho completo para o arquivo de interrupção."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), STOP_FEDERAL_KEY)


def criar_chave_interrupcao():
    """Cria o arquivo de interrupção."""
    caminho_chave = obter_caminho_chave_interrupcao()
    with open(caminho_chave, 'w', encoding='utf-8') as f:
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


def buscar_na_pasta_especifica(caminho_base, nome_banco):
    if not os.path.exists(caminho_base):
        return None

    try:
        todas_pastas_brutas = os.listdir(caminho_base)

        todas_pastas = [
            pasta for pasta in todas_pastas_brutas
            if not any(word.upper() in pasta.upper() for word in ["FILIAL", "ANTIGA"])
        ]

        resultado = process.extractOne(
            nome_banco, todas_pastas, score_cutoff=95)
        if resultado:
            pasta_encontrada = resultado[0]
            print(
                f"Pasta encontrada em '{caminho_base}': '{pasta_encontrada}' (Match Direto)")
            return os.path.join(caminho_base, pasta_encontrada)

        resultado_token = process.extractOne(
            nome_banco, todas_pastas, scorer=fuzz.token_set_ratio, score_cutoff=100)
        if resultado_token:
            pasta_encontrada = resultado_token[0]
            print(
                f"Pasta encontrada em '{caminho_base}': '{pasta_encontrada}' (Match Inteligente)")
            return os.path.join(caminho_base, pasta_encontrada)

        nome_banco_clean = remover_acentos(nome_banco).upper()
        for pasta in todas_pastas:
            pasta_clean = remover_acentos(pasta).upper()
            score = fuzz.token_set_ratio(nome_banco_clean, pasta_clean)
            if score == 100:
                print(
                    f"Pasta encontrada em '{caminho_base}': '{pasta}' (Match Sem Acentos)")
                return os.path.join(caminho_base, pasta)

        for pasta in todas_pastas:
            if pasta.upper() == nome_banco.upper():
                print(
                    f"Pasta encontrada em '{caminho_base}': '{pasta}' (Match Exato)")
                return os.path.join(caminho_base, pasta)

    except Exception as e:
        print(f"Erro ao ler pasta {caminho_base}: {e}")

    return None


def encontrar_pasta_empresa(nome_banco):
    resultado_principal = buscar_na_pasta_especifica(CAMINHO_REDE, nome_banco)
    if resultado_principal:
        return resultado_principal

    print(
        f"Empresa '{nome_banco}' não encontrada na raiz. Procurando em Sem Movimento...")
    resultado_sem_movimento = buscar_na_pasta_especifica(
        CAMINHO_SEM_MOVIMENTO, nome_banco)

    if resultado_sem_movimento:
        return resultado_sem_movimento

    print(
        f"ALERTA DE SEGURANÇA: Nenhuma pasta confiável encontrada para: '{nome_banco}'")
    print("O arquivo permanecerá na pasta Downloads para evitar erros.")
    return None


def encontrar_caminho_final(caminho_empresa):
    pasta_destino = caminho_empresa

    for variacao in VARIACOES_DOCS:
        try:
            for pasta_encontrada in os.listdir(caminho_empresa):
                caminho_completo = os.path.join(caminho_empresa, pasta_encontrada)
                if os.path.isdir(caminho_completo) and variacao.upper() in pasta_encontrada.upper():
                    pasta_destino = caminho_completo
                    print(f"Pasta de documentos encontrada: '{pasta_encontrada}' (contém '{variacao}')")
                    break
            else:
                continue
            break
        except Exception as e:
            print(f"Erro ao procurar pasta em {caminho_empresa}: {e}")

    variacoes_certidoes = ["CERTIDOES", "CERTIDÕES", "Certidoes", "Certidões"]

    for nome_pasta in variacoes_certidoes:
        caminho_teste = os.path.join(pasta_destino, nome_pasta)
        if os.path.exists(caminho_teste):
            return caminho_teste

    pasta_padrao = os.path.join(pasta_destino, "CERTIDOES")
    try:
        os.makedirs(pasta_padrao)
        return pasta_padrao
    except OSError:
        return pasta_destino


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
                    print(
                        f"Removendo arquivo antigo/fora do padrão: {arquivo}")
                    os.remove(caminho_completo)

    except Exception as e:
        print(f"Erro ao tentar limpar versões antigas: {e}")


def verificar_novo_arquivo(tempo_inicio, termos_ignorar=None, extensoes_permitidas=('.pdf',)):
    pasta_downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    padrao_busca = os.path.join(pasta_downloads, "*")

    arquivos = glob.glob(padrao_busca)
    arquivos = [f for f in arquivos if os.path.isfile(f)]

    if not arquivos:
        return None

    candidatos = []

    for caminho in arquivos:
        try:
            tempo_criacao = os.path.getctime(caminho)
        except OSError:
            continue

        if tempo_criacao <= tempo_inicio:
            continue

        nome_arquivo = os.path.basename(caminho).lower()

        # ignora temp
        if nome_arquivo.endswith(('.crdownload', '.tmp')):
            print(f"[DEBUG] arquivo temporario ignorado: {nome_arquivo}")
            continue

        # apenas pdf
        if extensoes_permitidas and not nome_arquivo.endswith(extensoes_permitidas):
            continue

        if termos_ignorar and any(termo.lower() in nome_arquivo for termo in termos_ignorar):
            print(f"arquivo ignorado pelo filtro '{termos_ignorar}': {nome_arquivo}")
            continue

        candidatos.append((tempo_criacao, caminho))

    if not candidatos:
        return None

    # pega o mais recente
    _, arquivo_mais_recente = max(candidatos, key=lambda x: x[0])
    print(f"[SUCESSO] Arquivo aceito: {os.path.basename(arquivo_mais_recente).lower()}")
    return arquivo_mais_recente


def mover_e_renomear(caminho_arquivo_origem, nome_empresa, tipo_certidao):
    print(f"[DEBUG] Emitindo certidão para empresa: {nome_empresa}")
    caminho_empresa = encontrar_pasta_empresa(nome_empresa)

    if not caminho_empresa:
        return False, "Pasta da empresa não encontrada no Z:"

    destino_final = encontrar_caminho_final(caminho_empresa)

    extensao = os.path.splitext(caminho_arquivo_origem)[1]
    tipo_certidao_limpo = (tipo_certidao or '').strip().upper()
    if tipo_certidao_limpo.startswith('CERTIDAO '):
        novo_nome = f"{tipo_certidao_limpo}{extensao}"
    else:
        novo_nome = f"CERTIDAO {tipo_certidao_limpo}{extensao}"

    limpar_versoes_antigas(destino_final, novo_nome, tipo_certidao)

    caminho_destino_completo = os.path.join(destino_final, novo_nome)

    try:
        shutil.move(caminho_arquivo_origem, caminho_destino_completo)
        return True, caminho_destino_completo
    except (OSError, PermissionError):
        try:
            shutil.copy2(caminho_arquivo_origem, caminho_destino_completo)
            os.remove(caminho_arquivo_origem)
            return True, caminho_destino_completo
        except (OSError, PermissionError) as e2:
            return False, str(e2)
