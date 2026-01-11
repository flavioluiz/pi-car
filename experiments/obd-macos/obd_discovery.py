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

# Altere para a porta do seu ELM327
PORT = "/dev/tty.OBDII"  # Ajuste conforme necessário

# Baudrates comuns para ELM327 Bluetooth
# 38400 é o mais comum, mas alguns usam 9600, 115200 ou 57600
BAUDRATE = 38400

def wake_up_adapter():
    """Acorda o adaptador ELM327 antes de usar a biblioteca obd"""
    print("Acordando o adaptador...")
    try:
        ser = serial.Serial(PORT, baudrate=BAUDRATE, timeout=2)
        time.sleep(1)
        ser.write(b'\r\r\r')
        time.sleep(0.5)
        ser.write(b'ATZ\r')
        time.sleep(2)
        response = ser.read(100)
        ser.close()
        if b'ELM' in response:
            print("Adaptador acordado!")
            return True
        return False
    except Exception as e:
        print(f"Erro ao acordar: {e}")
        return False

def discover_commands():
    print("Conectando ao OBD...")
    print(f"Porta: {PORT}")
    print(f"Baudrate: {BAUDRATE}")

    # Acorda o adaptador primeiro
    if not wake_up_adapter():
        print("AVISO: Não foi possível acordar o adaptador")

    time.sleep(1)

    # fast=False para inicialização mais confiável via Bluetooth
    # timeout maior para conexões Bluetooth
    connection = obd.OBD(
        portstr=PORT,
        baudrate=BAUDRATE,
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
    discover_commands()
