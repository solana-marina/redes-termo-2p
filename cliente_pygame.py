import pygame
import sys
import string
import queue
import time
from rede_cliente import NetworkThread

MAX_TENTATIVAS_PADRAO = 6
HOST_PADRAO = '127.0.0.1' 
PORTA_PADRAO = 12345

COR_BRANCO = (230, 230, 230)
COR_PRETO = (18, 18, 18)
COR_FUNDO = (18, 18, 18)
COR_CINZA = (58, 58, 60)
COR_BORDA = (80, 80, 80)
COR_VERDE = (106, 170, 100)
COR_AMARELO = (201, 180, 88)
COR_NEUTRO_TECLADO = (129, 131, 132)

MAPA_CORES_GUI = {
    'verde': COR_VERDE,
    'amarelo': COR_AMARELO,
    'cinza': COR_CINZA,
    'neutro': COR_NEUTRO_TECLADO
}

# Funções de Cálculo de Layout 

def calcular_dimensoes(largura_janela, altura_janela, tamanho_palavra, max_tentativas):

    dims = {}

    #1. Calcular o Tamanho de Célula
    largura_util = largura_janela * 0.95
    unidades_largura_teclado = 10 * 0.75 + 9 * 0.1
    unidades_largura_grid = tamanho_palavra * 1.1 
    
    divisor_largura = max(unidades_largura_teclado, unidades_largura_grid, 10)
    cell_size_w_max = largura_util / divisor_largura

    altura_util = altura_janela * 0.95
    total_unidades_h = 5.5 + (max_tentativas * 1.1)
    cell_size_h_max = altura_util / total_unidades_h

    dims['cell_size'] = min(cell_size_w_max, cell_size_h_max, 80) 
    dims['cell_margin'] = dims['cell_size'] * 0.1
    dims['key_h'] = dims['cell_size'] * 0.9
    dims['key_w'] = dims['cell_size'] * 0.75
    dims['key_margin'] = dims['cell_size'] * 0.1
    dims['key_w_special'] = dims['key_w'] * 1.5

    # 3. Calcular Tamanhos de Fonte 
    dims['font_grid_size'] = int(dims['cell_size'] * 0.7)
    dims['font_key_size'] = int(dims['key_h'] * 0.35)
    dims['font_notify_size'] = int(dims['key_h'] * 0.4)
    dims['font_button_size'] = int(dims['key_h'] * 0.38)
    
    # 4. Calcular Alturas Totais dos Componentes 
    dims['header_h'] = dims['font_notify_size'] * 2.5
    dims['grid_total_h'] = (max_tentativas * (dims['cell_size'] + dims['cell_margin'])) + dims['cell_margin']
    dims['notify_area_h'] = dims['key_h'] * 1.8
    dims['keyboard_total_h'] = (3 * (dims['key_h'] + dims['key_margin'])) + dims['key_margin']
    dims['bottom_margin'] = dims['key_margin']
    
    dims['min_window_h'] = (dims['header_h'] + dims['grid_total_h'] + 
                            dims['notify_area_h'] + dims['keyboard_total_h'] + 
                            dims['bottom_margin'])
    return dims

def carregar_fontes(dims):
    """Carrega (ou recarrega) todas as fontes com os novos tamanhos."""
    fontes = {}
    try:
        fontes['grid'] = pygame.font.SysFont('Arial', dims['font_grid_size'], bold=True)
        fontes['teclado'] = pygame.font.SysFont('Arial', dims['font_key_size'], bold=True)
        fontes['notificacao'] = pygame.font.SysFont('Arial', dims['font_notify_size'])
        fontes['botao'] = pygame.font.SysFont('Arial', dims['font_button_size'], bold=True)
    except:
        fontes['grid'] = pygame.font.Font(None, dims['font_grid_size'])
        fontes['teclado'] = pygame.font.Font(None, dims['font_key_size'])
        fontes['notificacao'] = pygame.font.Font(None, dims['font_notify_size'])
        fontes['botao'] = pygame.font.Font(None, dims['font_button_size'])
    return fontes

# Funções de Desenho

def desenhar_texto(surface, texto, pos, fonte, cor):
    try:
        text_surf = fonte.render(texto, True, cor)
        text_rect = text_surf.get_rect(center=pos)
        surface.blit(text_surf, text_rect)
    except Exception as e:
        print(f"Erro ao renderizar texto: {e}")

def desenhar_grid(surface, y_start, tentativas_feitas, tentativa_atual, linha_atual, tamanho_palavra, max_tentativas, dims, fontes):
    LARGURA_JANELA, ALTURA_JANELA = surface.get_size()
    
    largura_total_grid = (tamanho_palavra * (dims['cell_size'] + dims['cell_margin'])) - dims['cell_margin']
    offset_x = (LARGURA_JANELA - largura_total_grid) / 2
    offset_y = y_start
    cell_size = dims['cell_size']
    cell_margin = dims['cell_margin']
    
    for row in range(max_tentativas):
        for col in range(tamanho_palavra):
            x = offset_x + col * (cell_size + cell_margin)
            y = offset_y + row * (cell_size + cell_margin)
            rect = pygame.Rect(x, y, cell_size, cell_size)

            if row < linha_atual:
                palavra_passada, resultado = tentativas_feitas[row]
                letra = palavra_passada[col]
                cor_fundo = MAPA_CORES_GUI[resultado[col]]
                pygame.draw.rect(surface, cor_fundo, rect, border_radius=5)
                desenhar_texto(surface, letra.upper(), rect.center, fontes['grid'], COR_BRANCO)
            
            elif row == linha_atual:
                if col < len(tentativa_atual):
                    letra = tentativa_atual[col]
                    pygame.draw.rect(surface, COR_BORDA, rect, 2, border_radius=5)
                    desenhar_texto(surface, letra.upper(), rect.center, fontes['grid'], COR_BRANCO)
                else:
                    pygame.draw.rect(surface, COR_BORDA, rect, 2, border_radius=5)
            
            else:
                pygame.draw.rect(surface, COR_BORDA, rect, 2, border_radius=5)

def desenhar_teclado(surface, y_start, estado_teclado, dims, fontes):
    LARGURA_JANELA, ALTURA_JANELA = surface.get_size()
    
    linhas_teclado_chaves = [
        ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
        ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
        ['ENTER', 'z', 'x', 'c', 'v', 'b', 'n', 'm', 'BACK']
    ]
    
    largura_linhas_teclas = [
        [dims['key_w']] * 10,
        [dims['key_w']] * 9,
        [dims['key_w_special']] + [dims['key_w']] * 7 + [dims['key_w_special']]
    ]
    
    teclado_rects = {} 
    offset_y_base = y_start
    key_h = dims['key_h']
    key_margin = dims['key_margin']

    for i, linha_chaves in enumerate(linhas_teclado_chaves):
        linha_larguras = largura_linhas_teclas[i]
        largura_linha_total = sum(linha_larguras) + (len(linha_larguras) - 1) * key_margin
        
        offset_x = (LARGURA_JANELA - largura_linha_total) / 2
        y = offset_y_base + i * (key_h + key_margin)
        x_atual = offset_x
        
        for j, letra in enumerate(linha_chaves):
            largura_tecla_atual = linha_larguras[j]
            rect = pygame.Rect(x_atual, y, largura_tecla_atual, key_h)
            cor_letra_id = estado_teclado.get(letra.lower(), 'neutro')
            
            if letra == "ENTER" or letra == "BACK":
                cor_fundo = COR_NEUTRO_TECLADO
                cor_texto = COR_BRANCO
                pygame.draw.rect(surface, cor_fundo, rect, border_radius=5)
                desenhar_texto(surface, letra, rect.center, fontes['teclado'], cor_texto)
            
            elif cor_letra_id == 'verde_amarelo':
                rect_verde = pygame.Rect(x_atual, y, largura_tecla_atual / 2, key_h)
                rect_amarelo = pygame.Rect(x_atual + largura_tecla_atual / 2, y, largura_tecla_atual / 2, key_h)
                pygame.draw.rect(surface, COR_VERDE, rect_verde, border_top_left_radius=5, border_bottom_left_radius=5)
                pygame.draw.rect(surface, COR_AMARELO, rect_amarelo, border_top_right_radius=5, border_bottom_right_radius=5)
                desenhar_texto(surface, letra.upper(), rect.center, fontes['teclado'], COR_BRANCO)
            else:
                cor_fundo = MAPA_CORES_GUI.get(cor_letra_id, COR_NEUTRO_TECLADO)
                cor_texto = COR_BRANCO
                pygame.draw.rect(surface, cor_fundo, rect, border_radius=5)
                desenhar_texto(surface, letra.upper(), rect.center, fontes['teclado'], cor_texto)
            
            teclado_rects[letra] = rect
            x_atual += largura_tecla_atual + key_margin
    
    return teclado_rects

def desenhar_notificacao(surface, texto, y_pos_centro, fontes):
    if not texto:
        return
    LARGURA_JANELA, ALTURA_JANELA = surface.get_size()
    desenhar_texto(surface, texto, (LARGURA_JANELA / 2, y_pos_centro), fontes['notificacao'], COR_BRANCO)

def desenhar_botao(surface, texto, y_pos_centro, dims, fontes):
    LARGURA_JANELA, ALTURA_JANELA = surface.get_size()
    
    LARGURA_BOTAO = dims['key_w_special'] * 3
    ALTURA_BOTAO = dims['key_h']
    
    rect_botao = pygame.Rect(0, 0, LARGURA_BOTAO, ALTURA_BOTAO)
    rect_botao.center = (LARGURA_JANELA / 2, y_pos_centro)
    
    pygame.draw.rect(surface, COR_VERDE, rect_botao, border_radius=10)
    desenhar_texto(surface, texto, rect_botao.center, fontes['botao'], COR_BRANCO)
    
    return rect_botao

def desenhar_tela_login(surface, username_digitado, caixa_ativa, dims, fontes):
    LARGURA_JANELA, ALTURA_JANELA = surface.get_size()
    
    desenhar_texto(surface, "Termo Competitivo", (LARGURA_JANELA / 2, ALTURA_JANELA * 0.25),
                   fontes['grid'], COR_BRANCO)
    desenhar_texto(surface, "Digite seu nome:", (LARGURA_JANELA / 2, ALTURA_JANELA * 0.45),
                   fontes['notificacao'], COR_BRANCO)

    largura_caixa = LARGURA_JANELA * 0.4
    altura_caixa = dims['key_h']
    x_caixa = (LARGURA_JANELA - largura_caixa) / 2
    y_caixa = ALTURA_JANELA * 0.5
    
    rect_caixa = pygame.Rect(x_caixa, y_caixa, largura_caixa, altura_caixa)
    
    cor_borda_caixa = COR_BRANCO if caixa_ativa else COR_BORDA
    pygame.draw.rect(surface, cor_borda_caixa, rect_caixa, 2, border_radius=5)
    
    desenhar_texto(surface, username_digitado, rect_caixa.center, fontes['notificacao'], COR_BRANCO)
    desenhar_texto(surface, "Pressione ENTER para conectar", (LARGURA_JANELA / 2, y_caixa + altura_caixa + 40),
                   fontes['teclado'], COR_BORDA)
                   
    return rect_caixa

def desenhar_tela_espera(surface, fontes):
    LARGURA_JANELA, ALTURA_JANELA = surface.get_size()
    pontos = "." * (int(time.time() * 2) % 4)
    desenhar_texto(surface, f"Aguardando oponente{pontos}", 
                   (LARGURA_JANELA / 2, ALTURA_JANELA / 2),
                   fontes['notificacao'], COR_BRANCO)


#Loop Principal do Jogo (Cliente)
def main_pygame():
    pygame.init()
    pygame.font.init()
    
    # 2. Definir Tamanho Fixo da Janela (60% do monitor)
    info = pygame.display.Info()
    MONITOR_LARGURA = info.current_w
    MONITOR_ALTURA = info.current_h
    JANELA_LARGURA = int(MONITOR_LARGURA * 0.6)
    JANELA_ALTURA = int(MONITOR_ALTURA * 0.6)
    
    screen = pygame.display.set_mode((JANELA_LARGURA, JANELA_ALTURA))
    pygame.display.set_caption("Termo Competitivo")
    clock = pygame.time.Clock()

    game_state = "LOGIN" 
    network_thread = None
    fila_rede = queue.Queue()
    
    username_digitado = ""
    input_box_rect = None
    input_box_active = True
    
    tamanho_palavra = 5 
    max_tentativas = MAX_TENTATIVAS_PADRAO 
    
    tentativas_feitas = [] 
    tentativa_atual = "" 
    linha_atual = 0 
    estado_teclado = {letra: 'neutro' for letra in (string.ascii_lowercase + "enter" + "back")}
    meu_turno = False
    mensagem_notificacao = ""
    titulo_header = "Termo Competitivo"
    
    teclado_rects = {} 
    rect_botao_jogar_novamente = None 

    # 3. Calcular Dimensões e Fontes Iniciais (para tela de login)
    dims = calcular_dimensoes(JANELA_LARGURA, JANELA_ALTURA, 5, MAX_TENTATIVAS_PADRAO) 
    fontes = carregar_fontes(dims)

    # Loop Principal do Aplicativo
    rodando_app = True
    while rodando_app:
        
        # 6. Manipulação de Eventos (Comum a todos os estados)
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                rodando_app = False 

            # A. Eventos de MOUSE
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: 
                    
                    if game_state == "LOGIN":
                        if input_box_rect and input_box_rect.collidepoint(event.pos):
                            input_box_active = True
                        else:
                            input_box_active = False
                    
                    elif game_state == "PLAYING" and meu_turno:
                        for letra, rect in teclado_rects.items():
                            if rect.collidepoint(event.pos):
                                if letra == "ENTER":
                                    if len(tentativa_atual) == tamanho_palavra:
                                        network_thread.send_message("C_GUESS", {"word": tentativa_atual})
                                        tentativa_atual = ""
                                        meu_turno = False 
                                    else:
                                        mensagem_notificacao = f"A palavra deve ter {tamanho_palavra} letras!"
                                elif letra == "BACK":
                                    tentativa_atual = tentativa_atual[:-1]
                                    mensagem_notificacao = ""
                                else:
                                    if len(tentativa_atual) < tamanho_palavra:
                                        tentativa_atual += letra
                                        mensagem_notificacao = ""
                                break 
                                
                    elif game_state == "GAME_OVER":
                        if rect_botao_jogar_novamente and rect_botao_jogar_novamente.collidepoint(event.pos):
                            game_state = "WAITING"
                            tentativas_feitas = []
                            tentativa_atual = ""
                            linha_atual = 0
                            estado_teclado = {l: 'neutro' for l in estado_teclado}
                            mensagem_notificacao = ""
                            meu_turno = False
                            if network_thread: network_thread.stop()
                            network_thread = NetworkThread(HOST_PADRAO, PORTA_PADRAO, fila_rede, username_digitado)
                            network_thread.start()

            #B. Eventos de Teclado Físico
            if event.type == pygame.KEYDOWN:
                
                if game_state == "LOGIN":
                    if input_box_active:
                        if event.key == pygame.K_BACKSPACE:
                            username_digitado = username_digitado[:-1]
                        elif event.key == pygame.K_RETURN:
                            if username_digitado:
                                game_state = "WAITING"
                                network_thread = NetworkThread(HOST_PADRAO, PORTA_PADRAO, fila_rede, username_digitado)
                                network_thread.start()
                        elif event.unicode:
                            username_digitado += event.unicode
                        
                elif game_state == "PLAYING" and meu_turno:
                    if event.key == pygame.K_BACKSPACE:
                        tentativa_atual = tentativa_atual[:-1]
                        mensagem_notificacao = ""
                    
                    elif event.key == pygame.K_RETURN:
                        if len(tentativa_atual) == tamanho_palavra:
                            network_thread.send_message("C_GUESS", {"word": tentativa_atual})
                            tentativa_atual = ""
                            meu_turno = False 
                        else:
                            mensagem_notificacao = f"A palavra deve ter {tamanho_palavra} letras!"

                    elif event.unicode:
                        letra_bruta = event.unicode
                        if letra_bruta.isalpha(): 
                            if len(tentativa_atual) < tamanho_palavra:
                                tentativa_atual += letra_bruta
                                mensagem_notificacao = ""
        
        #7. Processamento da Fila de Rede
        try:
            while not fila_rede.empty():
                msg = fila_rede.get_nowait()
                tipo = msg.get("tipo")
                payload = msg.get("payload", {})
                
                if tipo == "S_WAITING":
                    game_state = "WAITING"
                
                elif tipo == "S_GAME_START":
                    tamanho_palavra = payload.get("tamanho_palavra", 5)
                    max_tentativas = payload.get("max_tentativas", 6)
                    
                    dims = calcular_dimensoes(JANELA_LARGURA, JANELA_ALTURA, tamanho_palavra, max_tentativas)
                    fontes = carregar_fontes(dims)
                    
                    titulo_header = f"Jogo contra {payload.get('oponente')}"
                    game_state = "PLAYING"
                
                elif tipo == "S_TURN_UPDATE":
                    if payload.get("proximo_turno_username") == username_digitado:
                        meu_turno = True
                        mensagem_notificacao = "É a sua vez!"
                    else:
                        meu_turno = False
                        mensagem_notificacao = f"Vez de {payload.get('proximo_turno_username')}..."
                
                elif tipo == "S_GAME_UPDATE":
                    tentativas_feitas.append(payload.get("tentativa"))
                    estado_teclado.update(payload.get("estado_teclado", {}))
                    linha_atual += 1
                    
                    if payload.get("proximo_turno_username") == username_digitado:
                        meu_turno = True
                        mensagem_notificacao = "É a sua vez!"
                    else:
                        meu_turno = False
                        mensagem_notificacao = f"Vez de {payload.get('proximo_turno_username')}..."
                
                elif tipo == "S_GAME_OVER_WIN" or tipo == "S_GAME_OVER_DRAW":
                    game_state = "GAME_OVER"
                    if payload.get("ultima_tentativa"):
                        tentativas_feitas.append(payload.get("ultima_tentativa"))
                    estado_teclado.update(payload.get("estado_teclado", {}))
                    linha_atual += 1
                    meu_turno = False
                    
                    if tipo == "S_GAME_OVER_WIN":
                        vencedor = payload.get('vencedor_username')
                        if vencedor == username_digitado:
                            mensagem_notificacao = f"Você venceu!"
                        else:
                            mensagem_notificacao = f"{vencedor} venceu!"
                    else:
                        mensagem_notificacao = "Empate!"
                    
                    if network_thread:
                        network_thread.stop()
                        network_thread = None

                #Trata a desconexão do oponente ---
                elif tipo == "S_ERROR":
                    mensagem = payload.get("mensagem", "Erro desconhecido")
                    mensagem_notificacao = mensagem
                    if "desconectou" in mensagem.lower():
                        game_state = "GAME_OVER"
                        meu_turno = False
                        if network_thread:
                            network_thread.stop()
                            network_thread = None
                
                elif tipo == "S_ERROR_FATAL":
                    mensagem_notificacao = payload.get("mensagem", "Erro fatal de rede")
                    game_state = "LOGIN"
                    if network_thread:
                        network_thread.stop()
                        network_thread = None

        except queue.Empty:
            pass
            
        #8. Renderização
        screen.fill(COR_FUNDO)
        
        y_cursor = 0 
        
        if game_state == "LOGIN":
            dims = calcular_dimensoes(JANELA_LARGURA, JANELA_ALTURA, 5, MAX_TENTATIVAS_PADRAO) 
            fontes = carregar_fontes(dims)
            input_box_rect = desenhar_tela_login(screen, username_digitado, input_box_active, dims, fontes)
            
        elif game_state == "WAITING":
            # Recalcula dims/fontes para a tela de espera
            if tamanho_palavra != 5 or max_tentativas != MAX_TENTATIVAS_PADRAO:
                 dims = calcular_dimensoes(JANELA_LARGURA, JANELA_ALTURA, 5, MAX_TENTATIVAS_PADRAO) 
                 fontes = carregar_fontes(dims)
            desenhar_tela_espera(screen, fontes)
            
        elif game_state == "PLAYING" or game_state == "GAME_OVER":
            # 1. Desenha o Título
            y_centro_header = dims['header_h'] / 2
            desenhar_texto(screen, titulo_header, 
                           (JANELA_LARGURA / 2, y_centro_header), 
                           fontes['notificacao'], COR_BRANCO)
            y_cursor += dims['header_h']
            
            # 2. Desenha o Grid (passando max_tentativas)
            desenhar_grid(screen, y_cursor, tentativas_feitas, tentativa_atual, linha_atual, tamanho_palavra, max_tentativas, dims, fontes)
            y_cursor += dims['grid_total_h']
            
            # 3. Define o Y para a ÁREA de notificação/botão
            y_area_notificacao_centro = y_cursor + (dims['notify_area_h'] / 2)
            y_cursor += dims['notify_area_h']
            
            # 4. Desenha o Teclado
            teclado_rects = desenhar_teclado(screen, y_cursor, estado_teclado, dims, fontes)
            
            # 5. Desenha Notificação OU Botão
            if game_state == "PLAYING":
                desenhar_notificacao(screen, mensagem_notificacao, y_area_notificacao_centro, fontes)
            else: # GAME_OVER
                y_pos_msg = y_area_notificacao_centro - (dims['notify_area_h'] * 0.25)
                y_pos_btn = y_area_notificacao_centro + (dims['notify_area_h'] * 0.25)
                
                desenhar_notificacao(screen, mensagem_notificacao, y_pos_msg, fontes)
                rect_botao_jogar_novamente = desenhar_botao(screen, "Jogar Novamente", y_pos_btn, dims, fontes)

        pygame.display.flip()
        clock.tick(60)
            
    if network_thread:
        network_thread.stop()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main_pygame()