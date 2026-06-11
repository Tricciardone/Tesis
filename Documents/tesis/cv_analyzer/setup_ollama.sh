#!/bin/bash

echo "🚀 Iniciando sistema CV Analyzer..."

# Esperar a que Ollama esté disponible
echo "⏳ Esperando que Ollama esté disponible..."
while ! curl -s http://ollama:11434/api/version > /dev/null; do
    echo "   Ollama no está listo, esperando 5 segundos..."
    sleep 5
done

echo "✅ Ollama está disponible!"

# Descargar modelo llama3.2:3b si no existe
echo "📥 Verificando modelo llama3.2:3b..."
if ! curl -s http://ollama:11434/api/tags | grep -q "llama3.2:3b"; then
    echo "📦 Descargando modelo llama3.2:3b (esto puede tomar varios minutos)..."
    curl -X POST http://ollama:11434/api/pull \
         -H "Content-Type: application/json" \
         -d '{"name": "llama3.2:3b"}' \
         --max-time 1800  # 30 minutos timeout
    
    if [ $? -eq 0 ]; then
        echo "✅ Modelo descargado exitosamente!"
    else
        echo "❌ Error descargando el modelo. Continuando sin él..."
    fi
else
    echo "✅ Modelo llama3.2:3b ya está disponible!"
fi

echo "🎉 Configuración completada!"
