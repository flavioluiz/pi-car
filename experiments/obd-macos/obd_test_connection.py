#!/usr/bin/env python3
"""
Script de diagnóstico para conexão OBD-II via Bluetooth no macOS
"""

import serial
import time

PORT = "/dev/tty.OBDII"
BAUDRATE = 38400  # Mais comum para ELM327 Bluetooth

def test_connection():
    print(f"Porta: {PORT}")
    print(f"Baudrate: {BAUDRATE}")
    print()

    try:
        ser = serial.Serial(
            PORT,
            baudrate=BAUDRATE,
            bytesize=8,
            parity='N',
            stopbits=1,
            timeout=5,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )

        print("Porta aberta. Aguardando adaptador acordar...")
        time.sleep(2)

        # Limpa buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # Alguns adaptadores precisam de um "wake up"
        print("Enviando bytes para acordar o adaptador...")
        ser.write(b'\r\r\r')
        time.sleep(1)
        ser.reset_input_buffer()

        # Tenta diferentes terminadores
        terminators = [
            (b'ATZ\r', 'ATZ + CR'),
            (b'ATZ\r\n', 'ATZ + CRLF'),
            (b'atz\r', 'atz minúsculo'),
        ]

        for cmd, desc in terminators:
            print(f"\nTentando: {desc}")
            ser.reset_input_buffer()
            ser.write(cmd)
            ser.flush()

            # Espera mais tempo pela resposta
            time.sleep(3)

            # Lê tudo disponível
            response = b''
            while ser.in_waiting > 0:
                response += ser.read(ser.in_waiting)
                time.sleep(0.1)

            if response:
                print(f"  RESPOSTA: {response}")
                print(f"  Decodificado: {response.decode('utf-8', errors='ignore')}")

                if b'ELM' in response or b'OK' in response:
                    print("\n*** CONEXÃO FUNCIONANDO! ***")
                    ser.close()
                    return True
            else:
                print("  (sem resposta)")

        ser.close()
        print("\n" + "="*50)
        print("DIAGNÓSTICO:")
        print("="*50)
        print("""
O adaptador não está respondendo. Possíveis causas:

1. BLUETOOTH NÃO ESTÁ REALMENTE CONECTADO
   - Abra Preferências do Sistema > Bluetooth
   - Verifique se o OBDII mostra "Conectado" (não apenas pareado)
   - Tente clicar no dispositivo e "Conectar"

2. O CARRO PRECISA ESTAR LIGADO
   - O ELM327 precisa de energia do carro para funcionar
   - Ligue a ignição (ACC) ou ligue o motor

3. TENTE RECONECTAR O BLUETOOTH
   - Desligue o Bluetooth do Mac
   - Desligue o carro por 10 segundos
   - Ligue o carro
   - Ligue o Bluetooth do Mac
   - Reconecte ao OBDII

4. VERIFIQUE O LED DO ADAPTADOR
   - Deve piscar ou acender quando energizado
   - Se não acender, pode estar com defeito
""")
        return False

    except serial.SerialException as e:
        print(f"Erro ao abrir porta: {e}")
        return False

if __name__ == "__main__":
    test_connection()
