import socket
import threading
import time

# Configurações de Rede Locais para o Colab
HOST = '127.0.0.1'
PORTA_NO_0 = 5000
PORTA_NO_1 = 5001

class NoSequenciadorMovel:
    def __init__(self, node_id, port, is_sequencer=False, next_port=None):
        self.node_id = node_id
        self.port = port
        self.is_sequencer = is_sequencer
        self.next_port = next_port
        self.sequence_number = 0
        self.message_count = 0
        self.migration_limit = 2 # Migra o papel após 2 mensagens para demonstração rápida
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def start(self):
        try:
            self.sock.bind((HOST, self.port))
            self.sock.listen(5)
            threading.Thread(target=self._accept_connections, daemon=True).start()
            print(f"-> [NÓ {self.node_id}] Iniciado na porta {self.port} | É Sequenciador? {self.is_sequencer}")
        except Exception as e:
            print(f"Erro ao iniciar Nó {self.node_id}: {e}")

    def _accept_connections(self):
        while True:
            try:
                conn, addr = self.sock.accept()
                threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()
            except:
                break

    def _handle_client(self, conn):
        try:
            data = conn.recv(1024).decode('utf-8')
            if not data:
                return
            
            # Protocolo de Migração do Sequenciador
            if data.startswith("MIGRATE_STATE"):
                _, seq_num = data.split(":")
                self.sequence_number = int(seq_num)
                self.is_sequencer = True
                print(f"\n[🔄 EVENTO DE MIGRAÇÃO] Nó {self.node_id} (Porta {self.port}) ASSUMIU O PAPEL DE SEQUENCIADOR MÓVEL! Seq Atual: {self.sequence_number}\n")
                conn.send("ACK_MIGRATION".encode('utf-8'))
                return

            # Processamento de Mensagem do Cliente
            if self.is_sequencer:
                self.sequence_number += 1
                self.message_count += 1
                resposta = f"[ORDEM GLOBAL #{self.sequence_number}] Mensagem: '{data}' (Processada pelo Sequenciador Nó {self.node_id})"
                print(f"[SEQUENCING NÓ {self.node_id}] {resposta}")
                conn.send(resposta.encode('utf-8'))
                
                # Gatilho de migração do papel móvel
                if self.message_count >= self.migration_limit and self.next_port:
                    self._trigger_migration()
            else:
                conn.send(f"ERRO: O Nó {self.port} não é o sequenciador ativo no momento.".encode('utf-8'))
                
        except Exception as e:
            print(f"Erro no manuseio do cliente: {e}")
        finally:
            conn.close()

    def _trigger_migration(self):
        print(f"\n[🔄 MIGRAÇÃO] Limite de {self.migration_limit} mensagens atingido no Nó {self.node_id}. Transferindo papel para a porta {self.next_port}...")
        self.is_sequencer = False
        self.message_count = 0
        
        try:
            mig_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            mig_sock.connect((HOST, self.next_port))
            mig_sock.send(f"MIGRATE_STATE:{self.sequence_number}".encode('utf-8'))
            mig_sock.recv(1024)
            mig_sock.close()
        except Exception as e:
            print(f"[ERRO NA MIGRAÇÃO] Falha ao contatar próximo nó: {e}")

def enviar_requisicao(porta_destino, mensagem):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, porta_destino))
        s.send(mensagem.encode('utf-8'))
        resposta = s.recv(1024).decode('utf-8')
        print(f"--- [CLIENTE] Resposta recebida: {resposta}")
        s.close()
    except Exception as e:
        print(f"Erro ao enviar para porta {porta_destino}: {e}")

# ==========================================
# SIMULAÇÃO PASSO A PASSO NO COLAB
# ==========================================
print("=== 1. INICIALIZANDO OS NÓS NA NUVEM ===")
no0 = NoSequenciadorMovel(node_id=0, port=PORTA_NO_0, is_sequencer=True, next_port=PORTA_NO_1)
no1 = NoSequenciadorMovel(node_id=1, port=PORTA_NO_1, is_sequencer=False, next_port=None)

no0.start()
no1.start()
time.sleep(1) # Aguarda os sockets subirem

print("\n=== 2. ENVIANDO MENSAGENS PARA TESTAR A ORDENAÇÃO E A MIGRAÇÃO ===")
print("Enviando Mensagem 1 para o Nó 0 (Sequenciador Atual)...")
enviar_requisicao(PORTA_NO_0, "Transação A (Compra)")

print("\nEnviando Mensagem 2 para o Nó 0 (Atingirá o limite de migração)...")
enviar_requisicao(PORTA_NO_0, "Transação B (Pagamento)")

print("\n--- O sequenciador acabou de migrar do Nó 0 para o Nó 1! ---")
print("Enviando Mensagem 3 para o NOVO sequenciador (Nó 1 na porta 5001)...")
enviar_requisicao(PORTA_NO_1, "Transação C (Entrega)")
