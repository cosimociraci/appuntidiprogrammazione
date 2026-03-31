import subprocess
import os

def formatta_codice_fedora(input_file, output_file, linguaggio="java"):
    # Mappatura Parser
    config = {
        "java": "java",
        "js": "babel",
        "thymeleaf": "html",
        "html": "html"
    }
    
    parser = config.get(linguaggio.lower(), "babel")

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            codice_grezzo = f.read()

        # Comando ottimizzato per Fedora/Linux
        # Usiamo npx per garantire che i plugin locali siano visti
        cmd = [
            'npx', 'prettier', 
            '--parser', parser, 
            '--tab-width', '4',
            '--print-width', '100'
        ]
        
        # Aggiungiamo il plugin solo se è Java
        if linguaggio.lower() == "java":
            cmd.extend(['--plugin', 'prettier-plugin-java'])

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate(input=codice_grezzo)

        if process.returncode == 0:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(stdout)
            print(f"✅ Codice formattato con successo in {output_file}")
        else:
            print(f"❌ Errore Prettier:\n{stderr}")

    except Exception as e:
        print(f"❌ Errore di sistema: {e}")

if __name__ == "__main__":
    # Assicurati che i file esistano prima di lanciare
    formatta_codice_fedora("codice_sporco.txt", "codice_pulito.txt", "java")