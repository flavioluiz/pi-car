# RTL-SDR Test Scripts

Scripts para testar a conectividade e funcionalidade do RTL-SDR no Raspberry Pi.

## Pre-requisitos

1. RTL-SDR conectado via USB ao Raspberry Pi
2. Pacotes do sistema instalados:
   ```bash
   sudo apt install rtl-sdr
   ```
3. Dependencias Python:
   ```bash
   pip3 install pyrtlsdr numpy --break-system-packages
   ```

## Verificacao Rapida

Antes de rodar os testes Python, verifique se o sistema reconhece o dispositivo:

```bash
# Verificar se o USB esta conectado
lsusb | grep -i rtl

# Testar com ferramenta do sistema
rtl_test -t
```

## Executar Teste Completo

```bash
cd ~/pi-car/experiments/rtlsdr-test
python3 rtlsdr_test.py
```

O script ira testar:
- Ferramentas do sistema (rtl_test, rtl_fm, rtl_power)
- Deteccao do dispositivo USB
- Importacao da biblioteca pyrtlsdr
- Abertura do dispositivo
- Sintonizacao de frequencias (FM e aviacao)
- Leitura de samples
- Ajustes de ganho

## Solucao de Problemas

### Dispositivo nao detectado
- Verifique a conexao USB
- Tente outra porta USB
- Execute `dmesg | tail` para ver mensagens do kernel

### Dispositivo ocupado
```bash
# Matar processos que podem estar usando o dispositivo
sudo killall rtl_fm rtl_test gqrx
```

### Erro de permissao
```bash
# Adicionar usuario ao grupo plugdev
sudo usermod -a -G plugdev $USER
# Fazer logout e login novamente
```

### pyrtlsdr nao encontrado
```bash
pip3 install pyrtlsdr --break-system-packages
```

## Frequencias de Teste

O script testa as seguintes frequencias:
- **99.5 MHz** - Radio FM
- **118.5 MHz** - Torre de aeroporto (AM)
- **433.92 MHz** - Banda ISM
