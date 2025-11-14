import socket
import threading
import json
import logica 
import string
from collections import Counter

HOST = '0.0.0.0'
PORTA = 12345
ARQUIVO_PALAVRAS = "palavras.txt"

clientes_conectados = {}
fila_de_espera = []
fila_lock = threading.Lock()
jogos_ativos = []

def enviar_mensagem(cliente_socket, tipo, payload):
    try:
        mensagem = json.dumps({"tipo": tipo, "payload": payload}) + '\n'
        cliente_socket.sendall(mensagem.encode('utf-8'))
    except Exception as e:
        print(f"[Erro Rede] Erro ao enviar para {cliente_socket.getpeername()}: {e}")

def broadcast_para_jogo(jogo_obj, tipo, payload, excluir_socket=None):
    for jogador_info in jogo_obj.jogador_turnos.values():
        if jogador_info["socket"] != excluir_socket:
            enviar_mensagem(jogador_info["socket"], tipo, payload)

class Jogo:
    def __init__(self, jogador1_info, jogador2_info, todas_palavras):
        self.palavra_secreta = logica.escolher_palavra_secreta(todas_palavras)
        self.tamanho_palavra = len(self.palavra_secreta)
        self.max_tentativas = self.tamanho_palavra + 1 
        
        self.tentativas_feitas = []
        self.jogador_turnos = {
            1: jogador1_info,
            2: jogador2_info
        }
        self.jogador_turnos[1]["numero"] = 1
        self.jogador_turnos[2]["numero"] = 2
        self.turno_atual = 1
        self.vencedor = None
        self.jogo_ativo = True
        
        self.socket_map = {
            jogador1_info["socket"]: self,
            jogador2_info["socket"]: self
        }
        jogos_ativos.append(self)
        print(f"[Jogo] Jogo criado entre {jogador1_info['username']} e {jogador2_info['username']}.")
        print(f"[Jogo] Palavra secreta: {self.palavra_secreta} (Tentativas: {self.max_tentativas})")

        self.iniciar_jogo()

    def iniciar_jogo(self):
        payload_base = {
            "tamanho_palavra": self.tamanho_palavra,
            "max_tentativas": self.max_tentativas 
        }

        # Payload para Jogador 1
        payload_j1 = payload_base.copy()
        payload_j1.update({
            "oponente": self.jogador_turnos[2]["username"],
            "seu_turno_num": 1
        })
        enviar_mensagem(self.jogador_turnos[1]["socket"], "S_GAME_START", payload_j1)
        
        # Payload para Jogador 2
        payload_j2 = payload_base.copy()
        payload_j2.update({
            "oponente": self.jogador_turnos[1]["username"],
            "seu_turno_num": 2
        })
        enviar_mensagem(self.jogador_turnos[2]["socket"], "S_GAME_START", payload_j2)
        
        self.enviar_atualizacao_turno()

    def processar_tentativa(self, jogador_socket, tentativa_normalizada):
        jogador_info = self.jogador_turnos[self.turno_atual]
        if jogador_socket != jogador_info["socket"]:
            enviar_mensagem(jogador_socket, "S_ERROR", {"mensagem": "Não é o seu turno."})
            return
        
        if len(tentativa_normalizada) != self.tamanho_palavra:
            enviar_mensagem(jogador_socket, "S_ERROR", {"mensagem": f"Palavra deve ter {self.tamanho_palavra} letras."})
            return

        resultado = logica.verificar_tentativa(tentativa_normalizada, self.palavra_secreta)
        self.tentativas_feitas.append((tentativa_normalizada, resultado))
        
        estado_teclado = logica.calcular_estado_teclado(self.tentativas_feitas, self.palavra_secreta)

        # Verificar vitória
        if tentativa_normalizada == self.palavra_secreta:
            self.vencedor = self.turno_atual
            self.jogo_ativo = False
            
            payload_vitoria = {
                "vencedor_username": jogador_info["username"],
                "palavra_secreta": self.palavra_secreta,
                "ultima_tentativa": (tentativa_normalizada, resultado),
                "estado_teclado": estado_teclado
            }
            broadcast_para_jogo(self, "S_GAME_OVER_WIN", payload_vitoria)
            self.encerrar_jogo()
            return
        
        if len(self.tentativas_feitas) == self.max_tentativas:
            self.jogo_ativo = False
            payload_empate = {
                "palavra_secreta": self.palavra_secreta,
                "ultima_tentativa": (tentativa_normalizada, resultado),
                "estado_teclado": estado_teclado
            }
            broadcast_para_jogo(self, "S_GAME_OVER_DRAW", payload_empate)
            self.encerrar_jogo()
            return

        # Se o jogo continua, troca o turno
        self.turno_atual = 2 if self.turno_atual == 1 else 1
        
        payload_update = {
            "jogador_que_jogou": jogador_info["username"],
            "tentativa": (tentativa_normalizada, resultado),
            "estado_teclado": estado_teclado,
            "proximo_turno_num": self.turno_atual,
            "proximo_turno_username": self.jogador_turnos[self.turno_atual]["username"]
        }
        broadcast_para_jogo(self, "S_GAME_UPDATE", payload_update)

    def enviar_atualizacao_turno(self):
        """Envia um lembrete de quem é a vez."""
        payload_turno = {
            "proximo_turno_num": self.turno_atual,
            "proximo_turno_username": self.jogador_turnos[self.turno_atual]["username"]
        }
        broadcast_para_jogo(self, "S_TURN_UPDATE", payload_turno)

    def desconectar_jogador(self, jogador_socket):
        if not self.jogo_ativo:
            return
            
        self.jogo_ativo = False
        jogador_info = clientes_conectados.get(jogador_socket, {"username": "Desconhecido"})
        print(f"[Jogo] Jogador {jogador_info['username']} desconectou. Encerrando jogo.")
        
        payload_dc = {
            "mensagem": f"Oponente {jogador_info['username']} desconectou. O jogo foi encerrado."
        }
        broadcast_para_jogo(self, "S_ERROR", payload_dc, excluir_socket=jogador_socket)
        self.encerrar_jogo()

    def encerrar_jogo(self):
        if self in jogos_ativos:
            jogos_ativos.remove(self)
        print("[Jogo] Jogo encerrado e limpo.")


#Gerenciamento de Clientes (Thread Principal)
def procurar_jogo(cliente_socket, username):
    global fila_de_espera
    
    jogador_info = {"socket": cliente_socket, "username": username}
    
    with fila_lock:
        print(f"[Matchmaking] {username} entrou na fila.")
        fila_de_espera.append(jogador_info)
        
        if len(fila_de_espera) >= 2:
            jogador1 = fila_de_espera.pop(0)
            jogador2 = fila_de_espera.pop(0)
            
            print(f"[Matchmaking] Formando jogo entre {jogador1['username']} e {jogador2['username']}")
            todas_palavras = logica.carregar_palavras(ARQUIVO_PALAVRAS)
            if todas_palavras:
                jogo = Jogo(jogador1, jogador2, todas_palavras)
                clientes_conectados[jogador1["socket"]] = {"username": jogador1["username"], "jogo": jogo}
                clientes_conectados[jogador2["socket"]] = {"username": jogador2["username"], "jogo": jogo}
            else:
                print("[Erro Fatal] Não foi possível carregar o banco de palavras.")
        else:
            enviar_mensagem(cliente_socket, "S_WAITING", {"mensagem": "Aguardando oponente..."})
            clientes_conectados[cliente_socket] = {"username": username, "jogo": None}


def handle_client(cliente_socket):
    buffer = ""
    try:
        while True:
            dados = cliente_socket.recv(4096).decode('utf-8')
            if not dados:
                break 
            
            buffer += dados
            
            while '\n' in buffer:
                mensagem_str, buffer = buffer.split('\n', 1)
                
                try:
                    mensagem_json = json.loads(mensagem_str)
                    tipo = mensagem_json.get("tipo")
                    payload = mensagem_json.get("payload", {})
                    
                    if tipo == "C_CONNECT":
                        username = payload.get("username", f"Jogador_{cliente_socket.getpeername()[1]}")
                        procurar_jogo(cliente_socket, username)
                    
                    elif tipo == "C_GUESS":
                        tentativa_bruta = payload.get("word", "").lower().strip()
                        tentativa_normalizada = logica.normalizar(tentativa_bruta)
                        
                        info_cliente = clientes_conectados.get(cliente_socket)
                        if info_cliente and info_cliente["jogo"]:
                            info_cliente["jogo"].processar_tentativa(cliente_socket, tentativa_normalizada)
                        else:
                            enviar_mensagem(cliente_socket, "S_ERROR", {"mensagem": "Você não está em um jogo."})
                            
                except json.JSONDecodeError:
                    print(f"[Erro Rede] Mensagem JSON mal formatada recebida.")
                except Exception as e:
                    print(f"[Erro Lógica] Erro ao processar mensagem: {e}")

    except ConnectionResetError:
        print(f"[Rede] Cliente {cliente_socket.getpeername()} desconectou abruptamente.")
    except Exception as e:
        print(f"[Rede] Erro inesperado com {cliente_socket.getpeername()}: {e}")
    finally:
        info_cliente_global = clientes_conectados.get(cliente_socket, {})
        username_desconectado = info_cliente_global.get('username', 'Desconhecido')
        print(f"[Rede] Cliente {username_desconectado} desconectou.")
        
        if info_cliente_global and info_cliente_global.get("jogo"):
            info_cliente_global["jogo"].desconectar_jogador(cliente_socket)
            
        with fila_lock:
            jogador_para_remover = None
            for jogador in fila_de_espera:
                if jogador["socket"] == cliente_socket:
                    jogador_para_remover = jogador
                    break
            if jogador_para_remover:
                fila_de_espera.remove(jogador_para_remover)
                print(f"[Matchmaking] Removido {username_desconectado} da fila.")
        
        if cliente_socket in clientes_conectados:
            del clientes_conectados[cliente_socket]
            
        cliente_socket.close()


def main():
    palavras = logica.carregar_palavras(ARQUIVO_PALAVRAS)
    if not palavras:
        print(f"[Erro Fatal] Não foi possível carregar '{ARQUIVO_PALAVRAS}'. Servidor não pode iniciar.")
        return
    print(f"[Info] {len(palavras)} palavras (normalizadas) carregadas com sucesso.")

    servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor_socket.bind((HOST, PORTA))
    servidor_socket.listen()
    print(f"[Servidor] Servidor 'Termo Competitivo' iniciado em {HOST}:{PORTA}")
    print("[Servidor] Aguardando conexões...")

    try:
        while True:
            cliente_socket, addr = servidor_socket.accept()
            print(f"[Rede] Nova conexão de {addr}")
            
            thread = threading.Thread(target=handle_client, args=(cliente_socket,))
            thread.daemon = True 
            thread.start()
            
    except KeyboardInterrupt:
        print("\n[Servidor] Desligando servidor (Ctrl+C)...")
    finally:
        servidor_socket.close()
        print("[Servidor] Servidor desligado.")

if __name__ == "__main__":
    main()