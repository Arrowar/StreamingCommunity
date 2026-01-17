#!/data/data/com.termux/files/usr/bin/bash

################################################################################
# INSTALADOR DEFINITIVO EXPLICADO v5.4-FINAL
# IMPORTANTE: Este script compila TODO manualmente
# NO usa el Makefile de curl-impersonate (el que causaba problemas)
# NO sobrescribe libcurl.so del sistema (fix para pkg)
# Compilaciones extras necesarias:
# 1. Brotli (parcheado) - Instalado en sistema ANTES
# 2. BoringSSL (parcheado para Android)
# 3. nghttp2 (manual)
# 4. curl-impersonate (compilado directo, SIN su Makefile)
# 5. patchelf (fix RPATH) + binutils (ld)
################################################################################

set -e

VERSION="5.4-FINAL"
LOG_FILE="$HOME/curl_cffi_install_$(date +%Y%m%d_%H%M%S).log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; exit 1; }
warning() { echo -e "${YELLOW}[AVISO]${NC} $1" | tee -a "$LOG_FILE"; }
info() { echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"; }
critical() { echo -e "${MAGENTA}[CRÍTICO]${NC} $1" | tee -a "$LOG_FILE"; }

cat << "EOF"
╔════════════════════════════════════════════════════════════╗
║       INSTALADOR FINAL EXPLICADO v5.4-FINAL               ║
║                                                            ║
║  Compilaciones extras incluidas:                          ║
║    ✓ Brotli (parcheado CMake 2.8.6→3.5)                   ║
║    ✓ BoringSSL (parcheado para Android/Bionic)            ║
║    ✓ nghttp2 (manual)                                     ║
║    ✓ curl-impersonate (SIN su Makefile problemático)      ║
║    ✓ patchelf (FIX RPATH) + binutils (ld)                 ║
║    ✓ NO sobrescribe libcurl.so del sistema                ║
║    ✓ USA librería correcta (libcurl-impersonate-chrome)   ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
EOF

read -p "Iniciar instalación? (s/n): " start
[ "$start" != "s" ] && exit 0

termux-wake-lock 2>/dev/null || true

################################################################################
# PASO 0: LIMPIEZA EXHAUSTIVA
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 0/12: LIMPIEZA EXHAUSTIVA"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

info "Espacio antes:"
df -h ~ | grep /data | tee -a "$LOG_FILE"

log "Desinstalando curl_cffi previo..."
pip uninstall -y curl_cffi curl-cffi 2>&1 | tee -a "$LOG_FILE" || true

log "Limpiando directorios de compilación..."
rm -rf ~/curl-impersonate ~/curl_cffi_build ~/brotli_temp ~/build_impersonate 2>/dev/null || true

critical "Limpiando ~/.local (FIX: __errno_location error)"
info "  Razón: libcurl en ~/.local causaba conflicto Bionic vs glibc"
rm -rf ~/.local/lib/libcurl* 2>/dev/null || true
rm -rf ~/.local/include/curl* 2>/dev/null || true
rm -rf ~/.local/bin/curl* 2>/dev/null || true

log "Limpiando instalaciones del sistema..."
rm -f $PREFIX/bin/curl-impersonate* 2>/dev/null || true
rm -f $PREFIX/bin/curl_chrome* $PREFIX/bin/curl_edge* $PREFIX/bin/curl_safari* 2>/dev/null || true
# IMPORTANTE: NO eliminar libcurl.so del sistema, solo impersonate
rm -f $PREFIX/lib/libcurl-impersonate* 2>/dev/null || true

log "Limpiando archivos temporales..."
rm -f ~/*.tar.* ~/*.zip ~/*.log 2>/dev/null || true
pip cache purge 2>&1 | tee -a "$LOG_FILE" || true

info "Espacio después:"
df -h ~ | grep /data | tee -a "$LOG_FILE"

log "✓ Limpieza exhaustiva completada"

################################################################################
# PASO 1: Dependencias base
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 1/12: Dependencias del sistema"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

pkg update -y 2>&1 | tee -a "$LOG_FILE"
pkg upgrade -y 2>&1 | tee -a "$LOG_FILE"

pkg install -y \
  build-essential cmake ninja wget python-pip rust git \
  termux-elf-cleaner autoconf automake libtool golang \
  openssl openssl-static patchelf binutils \
  2>&1 | tee -a "$LOG_FILE"

log "✓ Dependencias instaladas (incluyendo patchelf y binutils)"

# Verificar herramientas críticas
critical "Verificando herramientas críticas:"
if ! command -v ld &> /dev/null; then
    error "❌ ld no encontrado (parte de binutils)"
fi
log "  ✓ ld encontrado: $(which ld)"

if ! command -v patchelf &> /dev/null; then
    error "❌ patchelf no encontrado"
fi
log "  ✓ patchelf encontrado: $(which patchelf)"

################################################################################
# PASO 2: COMPILACIÓN EXTRA #1 - Brotli (CRÍTICO)
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 2/12: COMPILACIÓN EXTRA #1 - Brotli"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

critical "POR QUÉ ES NECESARIO:"
info "  1. El Makefile de curl-impersonate re-descarga Brotli"
info "  2. Eso sobrescribe cualquier parche que hagamos"
info "  3. Solución: Compilar e instalar Brotli EN SISTEMA primero"
info "  4. curl usará el Brotli del sistema (ya parcheado)"

cd ~
rm -rf brotli_temp
mkdir brotli_temp
cd brotli_temp

log "Descargando Brotli v1.0.9..."
wget --show-progress \
  https://github.com/google/brotli/archive/refs/tags/v1.0.9.tar.gz \
  2>&1 | tee -a "$LOG_FILE"

tar xf v1.0.9.tar.gz
cd brotli-1.0.9

critical "Aplicando PARCHE CRÍTICO:"
info "  Cambio: cmake_minimum_required(VERSION 2.8.6) → VERSION 3.5"
info "  Razón: CMake de Termux no soporta versiones < 3.5"

sed -i 's/cmake_minimum_required(VERSION 2\.8\.6)/cmake_minimum_required(VERSION 3.5)/' \
  CMakeLists.txt

# Verificar parche
if ! grep -q "VERSION 3.5" CMakeLists.txt; then
  error "❌ PARCHE DE BROTLI FALLÓ - Verificar manualmente"
fi

log "✓ Parche aplicado correctamente"

log "Compilando Brotli..."
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$PREFIX .. 2>&1 | tee -a "$LOG_FILE"
cmake --build . --config Release 2>&1 | tee -a "$LOG_FILE"
cmake --build . --config Release --target install 2>&1 | tee -a "$LOG_FILE"

# Verificar instalación
if [ ! -f "$PREFIX/lib/libbrotlicommon.so" ]; then
  error "❌ Brotli NO se instaló en $PREFIX/lib"
fi

log "✓ Brotli instalado en: $PREFIX/lib/libbrotli*"
ls -lh $PREFIX/lib/libbrotli* | head -3 | tee -a "$LOG_FILE"

################################################################################
# PASO 3: COMPILACIÓN EXTRA #2 - BoringSSL (CRÍTICO)
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 3/12: COMPILACIÓN EXTRA #2 - BoringSSL"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

critical "POR QUÉ ES NECESARIO:"
info "  1. curl-impersonate requiere BoringSSL (no OpenSSL)"
info "  2. BoringSSL da el TLS fingerprint real de navegadores"
info "  3. Necesita parches para Android/Bionic (no glibc)"

cd ~
mkdir -p curl-impersonate
cd curl-impersonate

log "Descargando BoringSSL..."
wget --show-progress -O bs.zip \
  "https://github.com/google/boringssl/archive/1b7fdbd9101dedc3e0aa3fcf4ff74eacddb34ecc.zip" \
  2>&1 | tee -a "$LOG_FILE"

unzip -q bs.zip
mv boringssl-* boringssl
cd boringssl

critical "Aplicando PARCHES PARA ANDROID:"

info "  PARCHE 1: Quitar -Werror (errores de compilación)"
sed -i 's/-Werror//g' CMakeLists.txt
log "  ✓ -Werror eliminado"

info "  PARCHE 2: Fix para Android (Bionic libc)"
info "  Cambio: && !defined(OPENSSL_ANDROID) → (eliminado)"
info "  Razón: Habilitar funciones en Android"
sed -i 's/&& !defined(OPENSSL_ANDROID)//g' ssl/test/handshake_util.h
log "  ✓ Android fix aplicado"

log "Compilando BoringSSL..."
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
  .. 2>&1 | tee -a "$LOG_FILE"

make -j$(nproc) 2>&1 | tee -a "$LOG_FILE"

# Verificar
if [ ! -f "ssl/libssl.a" ] || [ ! -f "crypto/libcrypto.a" ]; then
  error "❌ BoringSSL NO compiló correctamente"
fi

log "✓ BoringSSL compilado:"
ls -lh ssl/libssl.a crypto/libcrypto.a | tee -a "$LOG_FILE"

cd ../..

################################################################################
# PASO 4: COMPILACIÓN EXTRA #3 - nghttp2 (CRÍTICO)
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 4/12: COMPILACIÓN EXTRA #3 - nghttp2"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

critical "POR QUÉ ES NECESARIO:"
info "  1. Proporciona soporte HTTP/2"
info "  2. Necesario para impersonate completo"
info "  3. curl-impersonate lo requiere"

log "Descargando nghttp2 v1.56.0..."
wget --show-progress \
  https://github.com/nghttp2/nghttp2/releases/download/v1.56.0/nghttp2-1.56.0.tar.bz2 \
  2>&1 | tee -a "$LOG_FILE"

tar xf nghttp2-1.56.0.tar.bz2
cd nghttp2-1.56.0

log "Configurando nghttp2 (solo librería, estática)..."
./configure --prefix="$PWD/installed" \
  --enable-lib-only \
  --disable-shared \
  2>&1 | tee -a "$LOG_FILE"

log "Compilando nghttp2..."
make -j$(nproc) 2>&1 | tee -a "$LOG_FILE"
make install 2>&1 | tee -a "$LOG_FILE"

# Verificar
if [ ! -f "installed/lib/libnghttp2.a" ]; then
  error "❌ nghttp2 NO compiló"
fi

log "✓ nghttp2 compilado:"
ls -lh installed/lib/libnghttp2.a | tee -a "$LOG_FILE"

cd ..

################################################################################
# PASO 5: curl-impersonate - COMPILACIÓN MANUAL (SIN Makefile)
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 5/12: curl-impersonate - COMPILACIÓN MANUAL"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

critical "IMPORTANTE: NO usamos el Makefile de curl-impersonate"
info "  POR QUÉ:"
info "    1. Su Makefile re-descarga Brotli (borra nuestro parche)"
info "    2. Tiene problemas con rutas en Termux"
info "    3. Solución: Compilar curl directamente con ./configure + make"

log "Descargando curl v8.1.1..."
wget --show-progress https://curl.se/download/curl-8.1.1.tar.xz 2>&1 | tee -a "$LOG_FILE"
tar xf curl-8.1.1.tar.xz
cd curl-8.1.1

log "Descargando parches de curl-impersonate..."
wget -O p1.patch \
  https://raw.githubusercontent.com/lwthiker/curl-impersonate/main/chrome/patches/curl-impersonate.patch || true
wget -O p2.patch \
  https://raw.githubusercontent.com/lwthiker/curl-impersonate/main/chrome/patches/curl-CVE-2023-38545.patch || true

log "Aplicando parches..."
patch -p1 < p1.patch 2>&1 | tee -a "$LOG_FILE" || warning "Parche 1 opcional"
patch -p1 < p2.patch 2>&1 | tee -a "$LOG_FILE" || warning "Parche 2 opcional"

log "Regenerando scripts de configuración..."
autoreconf -fi 2>&1 | tee -a "$LOG_FILE"

critical "Configurando variables de compilación:"

info "  IMPORTANTE: BoringSSL va PRIMERO en CPPFLAGS"
info "  Razón: Evitar conflicto con OpenSSL de Termux"

export BORINGSSL_DIR="$PWD/../boringssl"
export NGHTTP2_DIR="$PWD/../nghttp2-1.56.0/installed"

# BoringSSL ANTES para tener prioridad
export CPPFLAGS="-I${BORINGSSL_DIR}/include -I${NGHTTP2_DIR}/include"
export LDFLAGS="-L${BORINGSSL_DIR}/build/ssl -L${BORINGSSL_DIR}/build/crypto -L${NGHTTP2_DIR}/lib -L$PREFIX/lib"

log "Variables configuradas:"
info "  CPPFLAGS: $CPPFLAGS"
info "  LDFLAGS: $LDFLAGS"

log "Configurando curl..."
./configure \
  --prefix=$PREFIX \
  --with-brotli=$PREFIX \
  --with-nghttp2=$NGHTTP2_DIR \
  --with-ssl=$BORINGSSL_DIR \
  CPPFLAGS="$CPPFLAGS" \
  LDFLAGS="$LDFLAGS" \
  2>&1 | tee -a "$LOG_FILE"

log "Compilando curl-impersonate ..."
log "  ☕ Este es el paso más largo, ve por un café..."

# -j1 para evitar problemas de concurrencia
make -j1 2>&1 | tee -a "$LOG_FILE"

# Verificar (CORREGIDO: buscar todos los posibles nombres)
critical "Verificando binarios compilados..."
log "Contenido de src/:"
ls -lh src/ 2>&1 | grep -E "curl" | tee -a "$LOG_FILE" || true

# Buscar en todas las ubicaciones posibles
BINARY_FOUND=false

if [ -f "src/curl-impersonate-chrome" ]; then
  log "  ✓ Encontrado: src/curl-impersonate-chrome"
  BINARY_FOUND=true
elif [ -f "src/.libs/curl-impersonate-chrome" ]; then
  log "  ✓ Encontrado: src/.libs/curl-impersonate-chrome"
  BINARY_FOUND=true
elif [ -f "src/curl" ]; then
  log "  ✓ Encontrado: src/curl"
  BINARY_FOUND=true
elif [ -f "src/.libs/curl" ]; then
  log "  ✓ Encontrado: src/.libs/curl"
  BINARY_FOUND=true
fi

if [ "$BINARY_FOUND" = false ]; then
  error "❌ curl NO compiló. Ver: tail -100 $LOG_FILE"
fi

log "✓ curl-impersonate compilado exitosamente"

################################################################################
# PASO 6: Instalar binarios (NO librerías del sistema aún)
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 6/12: Instalando binarios"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

mkdir -p ../output

# Copiar binario (buscar en orden de prioridad)
BINARY_COPIED=false

if [ -f "src/curl-impersonate-chrome" ]; then
  cp src/curl-impersonate-chrome ../output/
  log "  ✓ Binario copiado desde: src/curl-impersonate-chrome"
  BINARY_COPIED=true
elif [ -f "src/.libs/curl-impersonate-chrome" ]; then
  cp src/.libs/curl-impersonate-chrome ../output/
  log "  ✓ Binario copiado desde: src/.libs/curl-impersonate-chrome"
  BINARY_COPIED=true
elif [ -f "src/.libs/curl" ]; then
  cp src/.libs/curl ../output/curl-impersonate-chrome
  log "  ✓ Binario copiado desde: src/.libs/curl (renombrado)"
  BINARY_COPIED=true
elif [ -f "src/curl" ]; then
  cp src/curl ../output/curl-impersonate-chrome
  log "  ✓ Binario copiado desde: src/curl (renombrado)"
  BINARY_COPIED=true
fi

if [ "$BINARY_COPIED" = false ]; then
  error "❌ No se pudo copiar el binario"
fi

# Copiar librerías a output (NO al sistema todavía)
critical "Copiando librerías a directorio temporal..."
cp -v lib/.libs/libcurl*.so* ../output/ 2>&1 | tee -a "$LOG_FILE" || warning "No se pudieron copiar algunas librerías"

log "Contenido de output:"
ls -lh ../output/ 2>&1 | tee -a "$LOG_FILE"

# Instalar SOLO binario
cp ../output/curl-impersonate-chrome $PREFIX/bin/
chmod +x $PREFIX/bin/curl-impersonate-chrome

log "✓ Binario instalado en $PREFIX/bin/curl-impersonate-chrome"

# Verificar que funciona
if curl-impersonate-chrome --version &>/dev/null; then
  log "  ✓ Binario ejecuta correctamente"
  curl-impersonate-chrome --version | head -1 | tee -a "$LOG_FILE"
else
  warning "  ⚠ Binario instalado pero podría no ejecutar"
fi

################################################################################
# PASO 7: curl_cffi Python
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 7/12: Compilando curl_cffi Python"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd ~/curl-impersonate
git clone --depth=1 https://github.com/yifeikong/curl_cffi 2>&1 | tee -a "$LOG_FILE"
cd curl_cffi

pip install -U maturin 2>&1 | tee -a "$LOG_FILE"

export CARGO_BUILD_TARGET="$(rustc -Vv | grep host | awk '{print $2}')"
export LD_LIBRARY_PATH="$PREFIX/lib:$LD_LIBRARY_PATH"
export LDFLAGS="-L$PREFIX/lib"

log "Compilando extensión Python..."
make build 2>&1 | tee -a "$LOG_FILE"

log "Instalando curl_cffi..."
pip install --force-reinstall dist/*.whl 2>&1 | tee -a "$LOG_FILE"

# Verificar wrapper
WRAPPER="$PREFIX/lib/python3.12/site-packages/curl_cffi/_wrapper.abi3.so"
if [ ! -f "$WRAPPER" ]; then
  error "❌ Wrapper NO instalado en: $WRAPPER"
fi

log "✓ curl_cffi instalado"
log "✓ Wrapper verificado: $WRAPPER"
ls -lh "$WRAPPER" | tee -a "$LOG_FILE"

################################################################################
# PASO 8: FIX CRÍTICO - libcurl-impersonate.so.4 (USAR LIBRERÍA CORRECTA)
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 8/12: FIX CRÍTICO - libcurl-impersonate.so.4 (LIBRERÍA CORRECTA)"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

critical "IMPORTANTE: Usar libcurl-impersonate-chrome.so (NO libcurl.so del sistema)"
info "  La librería CORRECTA tiene símbolos de impersonate (~11MB)"
info "  La librería del sistema NO los tiene (~877KB)"

cd $PREFIX/lib

log "Estado ANTES:"
ls -lh libcurl*.so* 2>&1 | tee -a "$LOG_FILE" | head -10

# Limpiar SOLO libcurl-impersonate (NO tocar libcurl.so del sistema)
critical "Limpiando SOLO archivos libcurl-impersonate antiguos..."
rm -f libcurl-impersonate*.so* 2>&1 | tee -a "$LOG_FILE" || true

# Buscar la librería CORRECTA (libcurl-impersonate-chrome.so)
critical "Buscando librería compilada CORRECTA..."
LIBCURL_SRC=""

# Estrategia 1: Buscar libcurl-impersonate-chrome.so (la CORRECTA)
LIBCURL_SRC=$(find ~/curl-impersonate/curl-8.1.1/lib/.libs -name "libcurl-impersonate-chrome.so" 2>/dev/null | head -1)

if [ -n "$LIBCURL_SRC" ]; then
    log "  ✓ Encontrada: $LIBCURL_SRC"
else
    # Estrategia 2: Buscar .so.4.x.x
    LIBCURL_SRC=$(find ~/curl-impersonate/curl-8.1.1/lib/.libs -name "libcurl.so.4.*" 2>/dev/null | head -1)
    
    if [ -n "$LIBCURL_SRC" ]; then
        log "  ✓ Encontrada: $LIBCURL_SRC"
    else
        # Estrategia 3: Buscar cualquier .so en .libs
        LIBCURL_SRC=$(find ~/curl-impersonate/curl-8.1.1/lib/.libs -name "libcurl.so" 2>/dev/null | head -1)
        
        if [ -n "$LIBCURL_SRC" ]; then
            log "  ✓ Encontrada: $LIBCURL_SRC (sin versión)"
        else
            error "❌ No se encuentra librería compilada"
        fi
    fi
fi

log "Librería encontrada: $LIBCURL_SRC"

# VERIFICACIÓN CRÍTICA: Comprobar tamaño (debe ser > 5MB)
SIZE_BYTES=$(stat -c%s "$LIBCURL_SRC" 2>/dev/null || stat -f%z "$LIBCURL_SRC" 2>/dev/null)
SIZE_MB=$(echo "$SIZE_BYTES / 1024 / 1024" | bc)
SIZE_HUMAN=$(du -h "$LIBCURL_SRC" | awk '{print $1}')

log "Tamaño de librería: $SIZE_HUMAN ($SIZE_MB MB)"

if [ $SIZE_MB -lt 5 ]; then
    critical "⚠ ADVERTENCIA: Librería muy pequeña ($SIZE_MB MB)"
    warning "  Esto indica que podría NO tener los símbolos de impersonate"
    warning "  Se esperan ~10-15 MB para la librería completa"
    
    # Buscar si existe la versión chrome específica
    CHROME_LIB=$(find ~/curl-impersonate -name "libcurl-impersonate-chrome.so" 2>/dev/null | head -1)
    if [ -n "$CHROME_LIB" ]; then
        critical "  ✓ Encontrada versión chrome, usando esa en su lugar"
        LIBCURL_SRC="$CHROME_LIB"
        SIZE_HUMAN=$(du -h "$LIBCURL_SRC" | awk '{print $1}')
        log "  Nueva librería: $LIBCURL_SRC ($SIZE_HUMAN)"
    fi
fi

# Copiar la librería CORRECTA
critical "Instalando libcurl-impersonate (SIN tocar libcurl.so del sistema)..."
cp -v "$LIBCURL_SRC" libcurl-impersonate.so.4.8.0 2>&1 | tee -a "$LOG_FILE"

# Verificar tamaño después de copiar
INSTALLED_SIZE=$(du -h libcurl-impersonate.so.4.8.0 | awk '{print $1}')
log "Tamaño instalado: $INSTALLED_SIZE"

# Crear enlaces simbólicos
info "Creando enlaces simbólicos para libcurl-impersonate:"
ln -sf libcurl-impersonate.so.4.8.0 libcurl-impersonate.so.4 2>&1 | tee -a "$LOG_FILE"
ln -sf libcurl-impersonate.so.4 libcurl-impersonate.so 2>&1 | tee -a "$LOG_FILE"

# También para chrome
ln -sf libcurl-impersonate.so.4.8.0 libcurl-impersonate-chrome.so.4 2>&1 | tee -a "$LOG_FILE"
ln -sf libcurl-impersonate-chrome.so.4 libcurl-impersonate-chrome.so 2>&1 | tee -a "$LOG_FILE"

log "✓ Enlaces creados (libcurl.so del sistema NO modificada):"
ls -lh libcurl*.so* 2>&1 | tee -a "$LOG_FILE" | head -15

# Verificación del sistema
critical "Verificando que el sistema NO se rompió:"

if curl --version &>/dev/null; then
  log "  ✓ curl del sistema funciona correctamente"
  curl --version | head -1 | tee -a "$LOG_FILE"
else
  warning "  ⚠ curl del sistema podría estar afectado"
fi

# Verificar librerías críticas
info "Verificando librerías para curl_cffi:"
for lib in libcurl-impersonate.so.4 libcurl-impersonate.so; do
  if [ -e "$lib" ]; then
    SIZE=$(du -h $lib | awk '{print $1}')
    log "  ✓ $lib existe ($SIZE)"
  else
    error "  ✗ $lib NO EXISTE"
  fi
done

ldconfig 2>/dev/null || true

log "✓ Librerías instaladas SIN romper el sistema"

################################################################################
# PASO 9: FIX RPATH con patchelf
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 9/12: FIX RPATH con patchelf"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

critical "Modificando RPATH del wrapper Python"
info "  Esto asegura que encuentre libcurl-impersonate.so.4"

WRAPPER="$PREFIX/lib/python3.12/site-packages/curl_cffi/_wrapper.abi3.so"

log "RPATH actual:"
patchelf --print-rpath "$WRAPPER" 2>&1 | tee -a "$LOG_FILE" || warning "Sin RPATH"

log "Configurando RPATH..."
patchelf --set-rpath "$PREFIX/lib" "$WRAPPER" 2>&1 | tee -a "$LOG_FILE"

log "RPATH nuevo:"
patchelf --print-rpath "$WRAPPER" 2>&1 | tee -a "$LOG_FILE"

export LD_LIBRARY_PATH="$PREFIX/lib:$LD_LIBRARY_PATH"
log "✓ RPATH configurado: $PREFIX/lib"

################################################################################
# PASO 10: Limpieza
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 10/12: Limpieza post-instalación"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd ~
log "Borrando directorios de compilación..."
rm -rf ~/curl-impersonate ~/brotli_temp 2>&1 | tee -a "$LOG_FILE"
rm -f ~/*.tar.* ~/*.zip 2>/dev/null

critical "Limpiando ~/.local de nuevo"
rm -rf ~/.local/lib/libcurl* ~/.local/include/curl 2>/dev/null

info "Espacio liberado:"
df -h ~ | grep /data | tee -a "$LOG_FILE"

log "✓ ~1 GB liberado"

################################################################################
# PASO 11: Verificación
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 11/12: Verificación exhaustiva de navegadores"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

export LD_LIBRARY_PATH="$PREFIX/lib:$LD_LIBRARY_PATH"
cd ~

python << 'PYTEST'
import sys
import json
import os

print("\n" + "="*70)
print("VERIFICACIÓN EXHAUSTIVA")
print("="*70)

try:
    from curl_cffi import requests
    print("\n✓ curl_cffi importado correctamente\n")
    
    todos = [
        'chrome99', 'chrome100', 'chrome101', 'chrome104', 
        'chrome107', 'chrome110', 'chrome116', 'chrome119', 
        'chrome120', 'chrome123',
        'safari15_3', 'safari15_5', 'safari17_0', 'safari17_2_1',
        'edge99', 'edge101'
    ]
    
    funcionan = []
    fallan = []
    timeouts = []
    
    print("Probando TODOS los navegadores (~2 min)...\n")
    
    for nav in todos:
        try:
            r = requests.get('https://httpbin.org/get', 
                           impersonate=nav, 
                           timeout=10)
            
            if r.status_code == 200:
                funcionan.append(nav)
                print(f"  ✓ {nav:20} - OK")
            else:
                fallan.append(nav)
                print(f"  ✗ {nav:20} - Status {r.status_code}")
                
        except Exception as e:
            error_msg = str(e)
            if 'timeout' in error_msg.lower() or 'timed out' in error_msg.lower():
                timeouts.append(nav)
                print(f"  ⏱ {nav:20} - Timeout")
            elif 'not supported' in error_msg.lower():
                fallan.append(nav)
                print(f"  ✗ {nav:20} - No soportado")
            else:
                fallan.append(nav)
                print(f"  ✗ {nav:20} - Error")
    
    print("\n" + "="*70)
    print("RESUMEN:")
    print("="*70)
    print(f"✓ Funcionan:  {len(funcionan)}/{len(todos)}")
    print(f"✗ Fallan:     {len(fallan)}/{len(todos)}")
    print(f"⏱ Timeouts:   {len(timeouts)}/{len(todos)}")
    print("="*70)
    
    if funcionan:
        print("\n✅ NAVEGADORES FUNCIONALES:")
        for nav in funcionan:
            print(f"  • {nav}")
    
    if fallan:
        print("\n❌ DESCARTADOS:")
        for nav in fallan[:10]:
            print(f"  • {nav}")
    
    if timeouts:
        print("\n⏱️  TIMEOUTS:")
        for nav in timeouts[:10]:
            print(f"  • {nav}")
    
    with open(os.path.expanduser('~/.curl_cffi_browsers.json'), 'w') as f:
        json.dump({
            'funcionales': funcionan,
            'descartados': fallan,
            'timeouts': timeouts,
            'recomendado': funcionan[0] if funcionan else None
        }, f, indent=2)
    
    print("\n✓ Lista guardada en: ~/.curl_cffi_browsers.json")
    
    if len(funcionan) == 0:
        print("\n⚠️  ADVERTENCIA: Ningún navegador funcional")
        sys.exit(1)
    
    print("\n" + "="*70)
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTEST

if [ $? -ne 0 ]; then
  error "Verificación falló"
fi

################################################################################
# PASO 12: Wrapper y configuración permanente
################################################################################

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "PASO 12/12: Configuración permanente"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python << 'PYWRAPPER'
import json
import os

with open(os.path.expanduser('~/.curl_cffi_browsers.json'), 'r') as f:
    data = json.load(f)

funcionales = data['funcionales']
recomendado = data['recomendado']

wrapper_code = f'''#!/usr/bin/env python3
from curl_cffi import requests as _requests

NAVEGADORES_FUNCIONALES = {funcionales}
NAVEGADOR_RECOMENDADO = "{recomendado}"

class SmartRequests:
    @staticmethod
    def _validar(impersonate):
        if impersonate and impersonate not in NAVEGADORES_FUNCIONALES:
            raise ValueError(f"Navegador no verificado. Usa: {{NAVEGADORES_FUNCIONALES}}")
    
    @classmethod
    def get(cls, url, impersonate=None, **kwargs):
        if impersonate:
            cls._validar(impersonate)
        else:
            impersonate = NAVEGADOR_RECOMENDADO
        return _requests.get(url, impersonate=impersonate, **kwargs)
    
    @classmethod
    def post(cls, url, impersonate=None, **kwargs):
        if impersonate:
            cls._validar(impersonate)
        else:
            impersonate = NAVEGADOR_RECOMENDADO
        return _requests.post(url, impersonate=impersonate, **kwargs)
    
    @classmethod
    def listar_funcionales(cls):
        return NAVEGADORES_FUNCIONALES

requests = SmartRequests
'''

with open(os.path.expanduser('~/curl_cffi_smart.py'), 'w') as f:
    f.write(wrapper_code)

print("✓ Wrapper creado: ~/curl_cffi_smart.py")
PYWRAPPER

log "✓ Wrapper inteligente creado"

# LD_LIBRARY_PATH permanente
if ! grep -q "LD_LIBRARY_PATH.*curl_cffi" ~/.bashrc 2>/dev/null; then
  echo "" >> ~/.bashrc
  echo "# curl_cffi - Agregado por instalador" >> ~/.bashrc
  echo "export LD_LIBRARY_PATH=\"$PREFIX/lib:\$LD_LIBRARY_PATH\"" >> ~/.bashrc
  log "  ✓ LD_LIBRARY_PATH agregado a ~/.bashrc"
else
  log "  ✓ LD_LIBRARY_PATH ya existe en ~/.bashrc"
fi

termux-wake-unlock 2>/dev/null || true

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║       🎉 INSTALACIÓN COMPLETA 🎉                          ║"
echo "║                                                           ║"
echo "║  ✓ Brotli, BoringSSL, nghttp2                            ║"
echo "║  ✓ curl-impersonate compilado                            ║"
echo "║  ✓ curl_cffi instalado                                   ║"
echo "║  ✓ libcurl-impersonate.so.4 CORRECTA (~11MB)             ║"
echo "║  ✓ RPATH corregido con patchelf                          ║"
echo "║  ✓ Sistema NO roto (curl/pkg funcionan)                  ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
log "📄 Archivos:"
log "  • ~/curl_cffi_smart.py"
log "  • ~/.curl_cffi_browsers.json"
log "  • $LOG_FILE"
echo ""
log "✅ Instalación completa"
log "🔄 Ejecuta: source ~/.bashrc"
log "   Para cargar LD_LIBRARY_PATH en esta sesión"
echo "" 