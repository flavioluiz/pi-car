#!/usr/bin/env python3
"""
obd_discovery.py - Descobre todos os comandos OBD disponíveis no veículo

Script de teste para identificar quais comandos OBD-II são suportados
pelo veículo antes de integrar ao projeto pi-car principal.

Uso:
    python3 obd_discovery.py

Configuração:
    Ajuste a variável PORT para corresponder à porta do seu ELM327 no macOS
    (geralmente algo como /dev/tty.OBDII-SPPDev ou /dev/tty.ELM327)
"""

import obd
import serial
import time
import sys

# Altere para a porta do seu ELM327
PORT = "/dev/tty.usbmodemA86BB3EB03051"  # Ajuste conforme necessário

# Baudrates comuns para ELM327 USB (diferentes do Bluetooth!)
# USB adapters geralmente usam 9600, 38400, 115200 ou 500000
BAUDRATES_TO_TRY = [9600, 38400, 115200, 57600, 500000, 230400, 19200]

def find_baudrate():
    """Tenta encontrar o baudrate correto para o adaptador USB"""
    print("Procurando baudrate correto...")
    print(f"Porta: {PORT}\n")

    for baud in BAUDRATES_TO_TRY:
        print(f"Tentando {baud}...", end=" ")
        try:
            ser = serial.Serial(
                PORT,
                baudrate=baud,
                timeout=2,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            time.sleep(0.5)

            # Limpa o buffer
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # Envia comando ATZ (reset)
            ser.write(b'ATZ\r')
            time.sleep(1.5)

            response = ser.read(ser.in_waiting or 100)
            ser.close()

            if b'ELM' in response or b'elm' in response.lower():
                print(f"SUCESSO! Resposta: {response}")
                return baud
            elif response:
                print(f"Resposta: {response[:50]}...")
            else:
                print("Sem resposta")

        except serial.SerialException as e:
            print(f"Erro: {e}")
        except Exception as e:
            print(f"Erro: {e}")

    return None

def wake_up_adapter(baudrate):
    """Acorda o adaptador ELM327 antes de usar a biblioteca obd"""
    print("Acordando o adaptador...")
    try:
        ser = serial.Serial(PORT, baudrate=baudrate, timeout=2)
        time.sleep(0.5)
        ser.reset_input_buffer()
        ser.write(b'\r\r\r')
        time.sleep(0.3)
        ser.write(b'ATZ\r')
        time.sleep(1.5)
        response = ser.read(ser.in_waiting or 100)
        ser.close()
        if b'ELM' in response:
            print(f"Adaptador acordado! Resposta: {response}")
            return True
        print(f"Resposta inesperada: {response}")
        return False
    except Exception as e:
        print(f"Erro ao acordar: {e}")
        return False

def discover_commands(baudrate):
    print("\nConectando ao OBD...")
    print(f"Porta: {PORT}")
    print(f"Baudrate: {baudrate}")

    # Acorda o adaptador primeiro
    if not wake_up_adapter(baudrate):
        print("AVISO: Não foi possível acordar o adaptador")

    time.sleep(1)

    # fast=False para inicialização mais confiável
    connection = obd.OBD(
        portstr=PORT,
        baudrate=baudrate,
        fast=False,
        timeout=30
    )
    
    if not connection.is_connected():
        print("ERRO: Não foi possível conectar ao OBD")
        print(f"Status: {connection.status()}")
        return
    
    print(f"Conectado! Protocolo: {connection.protocol_name()}")
    print(f"Porta: {connection.port_name()}")
    print("\n" + "="*60)
    print("COMANDOS SUPORTADOS PELO VEÍCULO:")
    print("="*60 + "\n")
    
    supported = connection.supported_commands
    
    # Organizar por modo/categoria
    results = {}
    
    for cmd in supported:
        try:
            response = connection.query(cmd)
            value = response.value if response.value else "Sem valor"
            
            # Extrair magnitude se for uma unidade
            if hasattr(value, 'magnitude') and hasattr(value, 'units'):
                display = f"{value.magnitude} {value.units}"
            else:
                display = str(value)
            
            results[cmd.name] = {
                'desc': cmd.desc,
                'value': display,
                'unit': str(value.units) if hasattr(value, 'units') else None
            }
            
            print(f"✓ {cmd.name}")
            print(f"  Descrição: {cmd.desc}")
            print(f"  Valor: {display}")
            print()
            
        except Exception as e:
            print(f"✗ {cmd.name}: Erro - {e}")
            print()
    
    connection.close()
    
    # Resumo
    print("\n" + "="*60)
    print(f"TOTAL: {len(results)} comandos disponíveis")
    print("="*60)
    
    return results

if __name__ == "__main__":
    # Primeiro encontra o baudrate correto
    baudrate = find_baudrate()

    if baudrate:
        print(f"\n{'='*60}")
        print(f"Baudrate encontrado: {baudrate}")
        print(f"{'='*60}\n")
        discover_commands(baudrate)
    else:
        print("\n" + "="*60)
        print("ERRO: Não foi possível encontrar o baudrate correto.")
        print("Verifique:")
        print("  1. O adaptador está conectado?")
        print("  2. O veículo está ligado (ignição ON)?")
        print(f"  3. A porta {PORT} está correta?")
        print("="*60)
        sys.exit(1)
