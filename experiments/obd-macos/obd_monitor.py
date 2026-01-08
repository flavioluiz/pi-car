#!/usr/bin/env python3
"""
obd_monitor.py - Monitora dados OBD em tempo real

Script de teste para monitorar dados do veículo em tempo real antes de 
integrar ao projeto pi-car principal.

Uso:
    python3 obd_monitor.py

Configuração:
    Ajuste a variável PORT para corresponder à porta do seu ELM327 no macOS
    (geralmente algo como /dev/tty.OBDII-SPPDev ou /dev/tty.ELM327)
"""

import obd
import time

PORT = "/dev/tty.OBDII-SPPDev"

# Comandos principais a monitorar
COMMANDS = [
    obd.commands.RPM,
    obd.commands.SPEED,
    obd.commands.COOLANT_TEMP,
    obd.commands.THROTTLE_POS,
    obd.commands.ENGINE_LOAD,
    obd.commands.FUEL_LEVEL,
    obd.commands.INTAKE_TEMP,
    obd.commands.MAF,
]

def monitor():
    connection = obd.OBD(PORT)
    
    if not connection.is_connected():
        print("Falha na conexão")
        return
    
    print("Monitorando... (Ctrl+C para sair)\n")
    
    try:
        while True:
            print("\033[H\033[J")  # Limpa tela
            print("="*40)
            print("  PI-CAR OBD MONITOR")
            print("="*40)
            
            for cmd in COMMANDS:
                if cmd in connection.supported_commands:
                    r = connection.query(cmd)
                    if r.value:
                        print(f"{cmd.name:20} {r.value}")
                    else:
                        print(f"{cmd.name:20} --")
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nEncerrado.")
    
    connection.close()

if __name__ == "__main__":
    monitor()
