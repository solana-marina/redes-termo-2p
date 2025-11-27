import random
from collections import Counter
import unicodedata 
import string 

def normalizar(texto: str) -> str:
    texto = texto.lower()
    # Decompõe (ex: 'ç' -> 'c' + '̧')
    nfkd = unicodedata.normalize('NFKD', texto)
    # Codifica para ASCII, ignorando os acentos
    ascii_bytes = nfkd.encode('ascii', 'ignore')
    # Decodifica de volta para string
    return ascii_bytes.decode('utf-8')

def carregar_palavras(arquivo_palavras: str) -> set:
    try:
        with open(arquivo_palavras, 'r', encoding='utf-8') as f:
            palavras = {normalizar(linha.strip()) for linha in f if linha.strip()}
            
        palavras.discard("") 
        return palavras
    except FileNotFoundError:
        print(f"Erro: Arquivo de palavras '{arquivo_palavras}' não encontrado.")
        return set()

def escolher_palavra_secreta(todas_palavras: set) -> str | None:
    if not todas_palavras:
        return None  
    
    palavras_lista = list(todas_palavras)
    return random.choice(palavras_lista)

def verificar_tentativa(tentativa: str, palavra_secreta: str) -> list:
    tamanho = len(palavra_secreta)
    resultado = ['cinza'] * tamanho
    contagem_letras = Counter(palavra_secreta)
    
    # 1ª Passagem: Marcar todos os 'verde'
    for i in range(tamanho):
        letra_tentativa = tentativa[i]
        if letra_tentativa == palavra_secreta[i]:
            resultado[i] = 'verde'
            contagem_letras[letra_tentativa] -= 1
            
    # 2ª Passagem: Marcar todos os 'amarelo'
    for i in range(tamanho):
        if resultado[i] == 'verde':
            continue 
            
        letra_tentativa = tentativa[i]
        
        if letra_tentativa in contagem_letras and contagem_letras[letra_tentativa] > 0:
            resultado[i] = 'amarelo'
            contagem_letras[letra_tentativa] -= 1
            
    return resultado

def calcular_estado_teclado(tentativas_feitas, palavra_secreta):
    estado_teclado = {letra: 'neutro' for letra in string.ascii_lowercase}
    
    visto_verde = set()
    visto_amarelo = set()
    visto_cinza = set()
    posicoes_verdes_encontradas = {letra: set() for letra in string.ascii_lowercase}
    
    contagem_secreta = Counter(palavra_secreta)

    #Passagem 1: Iterar sobre todo o histórico de tentativas
    for (tentativa, resultado) in tentativas_feitas:
        for i, letra in enumerate(tentativa):
            cor_resultado = resultado[i]
            
            if letra not in estado_teclado:
                continue

            # Apenas rastreia o que foi visto
            if cor_resultado == 'verde':
                visto_verde.add(letra)
                posicoes_verdes_encontradas[letra].add(i) 
            elif cor_resultado == 'amarelo':
                visto_amarelo.add(letra)
            elif cor_resultado == 'cinza':
                visto_cinza.add(letra)

    #Passagem 2: Aplicar lógica de prioridade
    
    #Processa TODAS as letras vistas
    letras_relevantes = visto_verde.union(visto_amarelo).union(visto_cinza)
    
    for letra in letras_relevantes:
        foi_verde = letra in visto_verde
        foi_amarelo = letra in visto_amarelo

        # Prioridade 1: Verde (ou 🔰)
        if foi_verde:
            if foi_amarelo:
                # Foi verde E amarelo?
                num_verdes_encontrados = len(posicoes_verdes_encontradas[letra])
                total_na_palavra = contagem_secreta[letra]
                
                if num_verdes_encontrados == total_na_palavra:
                    # Todos os verdes foram encontrados, rebaixa 🔰 para 🟩
                    estado_teclado[letra] = 'verde'
                else:
                    # Ainda faltam verdes (que estão amarelos)
                    estado_teclado[letra] = 'verde_amarelo'
            else:
                # Só foi verde (nunca amarelo)
                estado_teclado[letra] = 'verde'
        
        # Prioridade 2: Amarelo
        elif foi_amarelo:
            # Só foi amarelo (e nunca verde)
            estado_teclado[letra] = 'amarelo'
        
        # Prioridade 3: Cinza
        elif letra in visto_cinza:
             # Só foi cinza (e nunca verde ou amarelo)
            estado_teclado[letra] = 'cinza'
            
    return estado_teclado