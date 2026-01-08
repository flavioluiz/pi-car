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

# Altere para a porta do seu ELM327
PORT = "/dev/tty.OBDII-SPPDev"  # Ajuste conforme necessário

def discover_commands():
    print("Conectando ao OBD...")
    connection = obd.OBD(PORT)
    
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
