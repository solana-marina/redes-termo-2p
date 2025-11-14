import socket
import threading
import json
import queue

class NetworkThread(threading.Thread):
    def __init__(self, host, porta, fila_rede, username):
        super().__init__()
        self.host = host
        self.porta = porta
        self.fila_rede = fila_rede 
        self.username = username
        self.socket = None
        self.rodando = True
        self.daemon = True # Garante que a thread morra se o app principal fechar

    def run(self):
        buffer = ""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.porta))
            
            # 1. Enviar a mensagem de conexão
            self.send_message("C_CONNECT", {"username": self.username})

            # 2. Loop de recebimento
            while self.rodando:
                dados = self.socket.recv(4096).decode('utf-8')
                if not dados:
                    if self.rodando:
                        # Servidor desconectou inesperadamente
                        break
                
                buffer += dados
                
                while '\n' in buffer:
                    mensagem_str, buffer = buffer.split('\n', 1)
                    try:
                        msg_json = json.loads(mensagem_str)
                        # Coloca a mensagem do servidor na fila para a GUI processar
                        self.fila_rede.put(msg_json)
                    except json.JSONDecodeError:
                        print(f"[Rede] JSON mal formatado recebido: {mensagem_str}")

        except ConnectionRefusedError:
            self.fila_rede.put({"tipo": "S_ERROR_FATAL", "payload": {"mensagem": "Não foi possível conectar ao servidor."}})
        except Exception as e:
            if self.rodando:
                print(f"[Rede] Erro na thread de rede: {e}")
                self.fila_rede.put({"tipo": "S_ERROR_FATAL", "payload": {"mensagem": f"Erro de rede: {e}"}})
        finally:
            if self.socket:
                self.socket.close()
            print("[Rede] Thread de rede finalizada.")

    def send_message(self, tipo, payload):
        if not self.socket or not self.rodando:
            return
            
        try:
            mensagem = json.dumps({"tipo": tipo, "payload": payload}) + '\n'
            self.socket.sendall(mensagem.encode('utf-8'))
        except Exception as e:
            print(f"[Rede] Erro ao enviar mensagem: {e}")

    def stop(self):
        self.rodando = False
        if self.socket:
            try:
                # Quebra o bloqueio de recv()
                self.socket.shutdown(socket.SHUT_RDWR) 
            except OSError:
                pass # Socket já pode estar fechado
            finally:
                self.socket.close()