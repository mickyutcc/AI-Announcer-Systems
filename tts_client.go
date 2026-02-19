package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
)

// Configuration
const (
	// Rachel Voice ID (Popular female voice)
	DefaultVoiceID = "21m00Tcm4TlvDq8ikWAM" 
	// Output file name
	OutputFileName = "tts_output.mp3"
	// Model ID - using multilingual v2 for better Thai support if needed
	ModelID = "eleven_multilingual_v2"
)

func main() {
	// 1. Load Configuration
	apiKey := loadEnv("ELEVENLABS_API_KEY")
	if apiKey == "" {
		fmt.Println("Error: ELEVENLABS_API_KEY not found in .env file")
		return
	}

	// Load optional configs or use defaults
	voiceID := loadEnv("ELEVENLABS_VOICE_ID")
	if voiceID == "" {
		voiceID = DefaultVoiceID
	}

	modelID := loadEnv("ELEVENLABS_MODEL_ID")
	if modelID == "" {
		modelID = ModelID
	}

	// 2. Determine text to speak
	text := "Hello! This is a test from MuseGen. สวัสดีครับ นี่คือการทดสอบเสียง"
	if len(os.Args) > 1 {
		text = strings.Join(os.Args[1:], " ")
	}

	fmt.Printf("Generating speech...\n")
	fmt.Printf("Voice ID: %s\n", voiceID)
	fmt.Printf("Model ID: %s\n", modelID)
	fmt.Printf("Text: \"%s\"\n", text)

	// 3. Call API
	err := generateSpeech(apiKey, voiceID, modelID, text)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Printf("✅ Success! Audio saved to: %s\n", OutputFileName)
}

// generateSpeech calls ElevenLabs API
func generateSpeech(apiKey, voiceID, modelID, text string) error {
	url := fmt.Sprintf("https://api.elevenlabs.io/v1/text-to-speech/%s", voiceID)

	// Payload
	payload := map[string]interface{}{
		"text":     text,
		"model_id": modelID,
		"voice_settings": map[string]float64{
			"stability":        0.5,
			"similarity_boost": 0.75,
		},
	}

	jsonData, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal json: %w", err)
	}

	// Create Request
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	// Headers
	req.Header.Set("xi-api-key", apiKey)
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Accept", "audio/mpeg")

	// Execute
	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("request failed: %w", err)
	}
	defer resp.Body.Close()

	// Check Response
	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("API returned status %d: %s", resp.StatusCode, string(body))
	}

	// Save to file
	outFile, err := os.Create(OutputFileName)
	if err != nil {
		return fmt.Errorf("failed to create output file: %w", err)
	}
	defer outFile.Close()

	_, err = io.Copy(outFile, resp.Body)
	if err != nil {
		return fmt.Errorf("failed to write to file: %w", err)
	}

	return nil
}

// loadEnv reads .env file and extracts value for key
func loadEnv(targetKey string) string {
	data, err := os.ReadFile(".env")
	if err != nil {
		return ""
	}

	lines := strings.Split(string(data), "\n")
	for _, line := range lines {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "#") || line == "" {
			continue
		}
		
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}

		key := strings.TrimSpace(parts[0])
		val := strings.TrimSpace(parts[1])

		if key == targetKey {
			// Remove quotes if present
			val = strings.Trim(val, `"'`)
			return val
		}
	}
	return ""
}
