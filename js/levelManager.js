/**
 * LevelManager: Sistema modular para carga de niveles en bloques y carpetas.
 * Soporta nomenclatura de hasta 6 cifras (000001 a 999999).
 * Estructura de carpetas: data/levels/XXXXXX-YYYYYY/levels_XXXXXX-YYYYYY.json
 * Ejemplo: data/levels/000001-001000/levels_000001-000100.json
 */
class LevelManager {
  constructor(options = {}) {
    this.basePath = options.basePath || 'data/levels';
    this.folderRangeSize = options.folderRangeSize || 1000; // 1,000 niveles por carpeta
    this.fileRangeSize = options.fileRangeSize || 100;       // 100 niveles por archivo JSON
    this.maxLevel = options.maxLevel || 999999;             // Hasta 6 dígitos
    
    // Caché en memoria de los archivos JSON cargados: key -> Array<Level>
    this.loadedChunks = new Map();
    // Mapa indexado directo por ID para acceso O(1): levelId -> Level
    this.levelCache = new Map();
  }

  /**
   * Formatea un número a cadena de 6 dígitos con ceros a la izquierda.
   * Ej: 5 -> '000005', 100 -> '000100'
   */
  pad6(num) {
    return String(num).padStart(6, '0');
  }

  /**
   * Obtiene la ruta relativa del archivo JSON correspondiente a un ID de nivel.
   * Nivel 1   -> data/levels/000001-001000/levels_000001-000100.json
   * Nivel 150 -> data/levels/000001-001000/levels_000101-000200.json
   * Nivel 1050-> data/levels/001001-002000/levels_001001-001100.json
   */
  getLevelFilePath(levelId) {
    if (levelId < 1 || levelId > this.maxLevel) {
      throw new Error(`El nivel ${levelId} está fuera del rango permitido (1 - ${this.maxLevel}).`);
    }

    // Calcular rango de carpeta (ej. 1 a 1000, 1001 a 2000)
    const folderIndex = Math.floor((levelId - 1) / this.folderRangeSize);
    const folderStart = folderIndex * this.folderRangeSize + 1;
    const folderEnd = Math.min((folderIndex + 1) * this.folderRangeSize, this.maxLevel);
    const folderName = `${this.pad6(folderStart)}-${this.pad6(folderEnd)}`;

    // Calcular rango de archivo (ej. 1 a 100, 101 a 200)
    const fileIndex = Math.floor((levelId - 1) / this.fileRangeSize);
    const fileStart = fileIndex * this.fileRangeSize + 1;
    const fileEnd = Math.min((fileIndex + 1) * this.fileRangeSize, this.maxLevel);
    const fileName = `levels_${this.pad6(fileStart)}-${this.pad6(fileEnd)}.json`;

    return `${this.basePath}/${folderName}/${fileName}`;
  }

  /**
   * Carga el archivo JSON que contiene el nivel solicitado y lo almacena en caché.
   */
  async loadChunkForLevel(levelId) {
    const filePath = this.getLevelFilePath(levelId);
    
    if (this.loadedChunks.has(filePath)) {
      return this.loadedChunks.get(filePath);
    }

    try {
      const response = await fetch(filePath);
      if (!response.ok) {
        throw new Error(`No se pudo cargar el archivo ${filePath}: HTTP ${response.status}`);
      }
      const levelsArray = await response.json();
      
      this.loadedChunks.set(filePath, levelsArray);
      levelsArray.forEach(lvl => {
        this.levelCache.set(lvl.id, lvl);
      });

      return levelsArray;
    } catch (err) {
      console.warn(`[LevelManager] Archivo remoto no disponible (${filePath}).`, err.message);
      return null;
    }
  }

  /**
   * Obtiene la configuración de un nivel por su ID.
   * Si no está en memoria, intenta cargarlo vía fetch asíncrono.
   */
  async getLevel(levelId) {
    if (this.levelCache.has(levelId)) {
      return this.levelCache.get(levelId);
    }

    await this.loadChunkForLevel(levelId);
    return this.levelCache.get(levelId) || null;
  }

  /**
   * Precarga o registra niveles en memoria (útil para fallback o datos iniciales).
   */
  registerLevels(levelsArray) {
    if (!Array.isArray(levelsArray)) return;
    levelsArray.forEach(lvl => {
      this.levelCache.set(lvl.id, lvl);
    });
  }

  /**
   * Retorna una lista con los IDs de los niveles que están actualmente en memoria.
   */
  getCachedLevelIds() {
    return Array.from(this.levelCache.keys()).sort((a, b) => a - b);
  }
}

// Exportación global para navegadores
window.LevelManager = LevelManager;

