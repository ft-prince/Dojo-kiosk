/**
 * SecuGen Biometric Client Library
 * JavaScript library for communicating with SecuGen Client Bridge
 *
 * Usage:
 *   const bio = new BiometricClient();
 *   const status = await bio.getStatus();
 *   const capture = await bio.captureFingerprint();
 */

class BiometricClient {
  constructor(baseUrl = "http://localhost:5000") {
    this.baseUrl = baseUrl;
    this.connected = false;
  }

  /**
   * Check if the client bridge and device are connected
   * @returns {Promise<Object>} Status object
   */
  async getStatus() {
    try {
      const response = await fetch(`${this.baseUrl}/status`);
      const data = await response.json();
      this.connected = data.connected;
      return {
        success: true,
        connected: data.connected,
        width: data.width,
        height: data.height,
      };
    } catch (error) {
      this.connected = false;
      return {
        success: false,
        connected: false,
        error: error.message,
      };
    }
  }

  /**
   * Capture fingerprint image and generate template
   * @returns {Promise<Object>} Capture result with image, template, and quality
   */
  async captureFingerprint() {
    if (!this.connected) {
      return {
        success: false,
        error: "Device not connected. Please check connection.",
      };
    }

    try {
      const response = await fetch(`${this.baseUrl}/capture`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        const error = await response.json();
        return {
          success: false,
          error: error.error || "Capture failed",
        };
      }

      const data = await response.json();
      return {
        success: true,
        image: data.image, // Base64 encoded image
        template: data.template, // Base64 encoded template
        quality: data.quality, // Quality score 0-100
        width: data.width,
        height: data.height,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Get a single preview frame (no template generation)
   * Useful for live preview functionality
   * @returns {Promise<Object>} Preview frame
   */
  async getLivePreview() {
    if (!this.connected) {
      return {
        success: false,
        error: "Device not connected",
      };
    }

    try {
      const response = await fetch(`${this.baseUrl}/live-preview`);

      if (!response.ok) {
        const error = await response.json();
        return {
          success: false,
          error: error.error || "Preview failed",
        };
      }

      const data = await response.json();
      return {
        success: true,
        image: data.image,
        quality: data.quality,
        width: data.width,
        height: data.height,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Match two fingerprint templates
   * @param {string} template1 - Base64 encoded template
   * @param {string} template2 - Base64 encoded template
   * @returns {Promise<Object>} Match result
   */
  async matchTemplates(template1, template2) {
    if (!this.connected) {
      return {
        success: false,
        error: "Device not connected",
      };
    }

    try {
      const response = await fetch(`${this.baseUrl}/match`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          template1: template1,
          template2: template2,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        return {
          success: false,
          error: error.error || "Match failed",
        };
      }

      const data = await response.json();
      return {
        success: data.success,
        matched: data.matched,
      };
    } catch (error) {
      return {
        success: false,
        error: error.message,
      };
    }
  }

  /**
   * Display fingerprint image in a canvas element
   * @param {string} imageBase64 - Base64 encoded grayscale image
   * @param {number} width - Image width
   * @param {number} height - Image height
   * @param {HTMLCanvasElement} canvas - Canvas element to draw on
   */
  displayImage(imageBase64, width, height, canvas) {
    try {
      // Decode base64 to binary
      const binaryString = atob(imageBase64);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Create ImageData
      const imageData = new ImageData(width, height);
      for (let i = 0; i < bytes.length; i++) {
        const pixelIndex = i * 4;
        const value = bytes[i];
        imageData.data[pixelIndex] = value; // R
        imageData.data[pixelIndex + 1] = value; // G
        imageData.data[pixelIndex + 2] = value; // B
        imageData.data[pixelIndex + 3] = 255; // A
      }

      // Draw to canvas
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext("2d");
      ctx.putImageData(imageData, 0, 0);

      return true;
    } catch (error) {
      console.error("Display error:", error);
      return false;
    }
  }

  /**
   * Create an image element from base64 fingerprint data
   * @param {string} imageBase64 - Base64 encoded image
   * @param {number} width - Image width
   * @param {number} height - Image height
   * @returns {HTMLImageElement} Image element
   */
  createImageElement(imageBase64, width, height) {
    const canvas = document.createElement("canvas");
    this.displayImage(imageBase64, width, height, canvas);

    const img = new Image();
    img.src = canvas.toDataURL();
    return img;
  }

  /**
   * Start live preview loop
   * Continuously captures frames and calls callback
   * @param {Function} callback - Function(image, quality)
   * @param {number} intervalMs - Interval in milliseconds (default 200ms)
   * @returns {Object} Control object with stop() method
   */
  startLivePreview(callback, intervalMs = 200) {
    let running = true;
    let intervalId = null;

    const loop = async () => {
      if (!running) return;

      const preview = await this.getLivePreview();
      if (preview.success) {
        callback(preview.image, preview.quality, preview.width, preview.height);
      }

      if (running) {
        intervalId = setTimeout(loop, intervalMs);
      }
    };

    loop();

    return {
      stop: () => {
        running = false;
        if (intervalId) {
          clearTimeout(intervalId);
        }
      },
    };
  }
}

// Make available globally
if (typeof window !== "undefined") {
  window.BiometricClient = BiometricClient;
}

// Export for module systems
if (typeof module !== "undefined" && module.exports) {
  module.exports = BiometricClient;
}
