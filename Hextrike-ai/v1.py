#!/usr/bin/env python3
"""
AI-Guided Penetration Testing with Scope Management
Combines Ollama AI decision-making with Hexstrike tools
"""
import requests
import json
import time
from datetime import datetime

# Configuration
Hexstrike = "http://192.168.2.154:8888"
OLLAMA = "http://192.168.2.151:11434"
OLLAMA_MODEL = "llama3.1:8b"  # or "qwen2.5:7b"

# ============= SCOPE DEFINITION =============
SCOPE = {
    "target": "example.com",  # Main target
    "target_type": "web_application",  # Options: web_application, network, api, mobile
    
    # In-scope items
    "in_scope": [
        "example.com",
        "*.example.com",  # All subdomains
        # Add more in-scope targets
    ],
    
    # Out-of-scope items (will be blocked)
    "out_of_scope": [
        "admin.example.com",  # Example: admin panel
        # Add sensitive areas
    ],
    
    # Testing constraints
    "constraints": {
        "max_threads": 10,
        "rate_limit": "100/minute",  # Requests per minute
        "time_limit": 3600,  # Max test duration in seconds (1 hour)
        "allowed_tools": [  # Restrict which tools can be used
            "nmap", "subfinder", "whatweb", "nuclei", 
            "httpx", "nikto", "sqlmap", "gobuster"
        ],
        "forbidden_tools": [  # Never use these
            "metasploit", "hydra", "medusa"  # No brute forcing
        ]
    },
    
    # Test objectives
    "objectives": [
        "subdomain_discovery",
        "technology_detection", 
        "vulnerability_scanning",
        "security_headers_check"
    ],
    
    # Sensitivity level
    "sensitivity": "moderate",  # Options: passive, moderate, aggressive
    
    # Authorization details
    "authorization": {
        "authorized_by": "Security Team",
        "authorization_date": "2024-01-15",
        "engagement_type": "authorized_pentest"  # or "bug_bounty", "ctf"
    }
}
# ============================================

def check_scope(target):
    """Verify target is within scope"""
    # Check if target is in out_of_scope
    for out in SCOPE['out_of_scope']:
        if out in target:
            return False, f"Target '{target}' is OUT OF SCOPE"
    
    # Check if target matches in_scope patterns
    for in_scope in SCOPE['in_scope']:
        if '*' in in_scope:
            # Wildcard matching
            pattern = in_scope.replace('*.', '')
            if pattern in target:
                return True, f"Target '{target}' is IN SCOPE"
        elif in_scope in target:
            return True, f"Target '{target}' is IN SCOPE"
    
    return False, f"Target '{target}' not found in scope definition"

def check_tool_allowed(tool):
    """Check if tool is allowed in scope"""
    if tool in SCOPE['constraints']['forbidden_tools']:
        return False, f"Tool '{tool}' is FORBIDDEN by scope"
    
    if SCOPE['constraints']['allowed_tools'] and \
       tool not in SCOPE['constraints']['allowed_tools']:
        return False, f"Tool '{tool}' is NOT in allowed list"
    
    return True, f"Tool '{tool}' is allowed"

def ask_ollama(question, context=""):
    """Ask Ollama for pentesting advice"""
    full_prompt = f"""{context}

{question}

Remember: You are a professional penetration tester. Be specific and technical."""
    
    try:
        response = requests.post(f"{OLLAMA}/api/generate", json={
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9
            }
        }, timeout=60)
        
        if response.status_code == 200:
            return response.json()['response']
        else:
            return f"Error: Ollama returned {response.status_code}"
    except Exception as e:
        return f"Error communicating with Ollama: {e}"

def execute_Hexstrike_command(cmd, description=""):
    """Execute command via Hexstrike with error handling"""
    print(f"[+] {description}")
    print(f"    Command: {cmd}")
    
    try:
        response = requests.post(f"{Hexstrike}/api/command", 
                                json={"command": cmd}, 
                                timeout=300)  # 5 min timeout
        
        if response.status_code == 200:
            result = response.json()
            output = result.get('output', 'No output')
            return True, output
        else:
            return False, f"HTTP Error {response.status_code}"
    except Exception as e:
        return False, f"Error: {e}"

def print_scope_summary():
    """Display scope information"""
    print("\n" + "="*70)
    print("PENETRATION TEST SCOPE")
    print("="*70)
    print(f"Target:          {SCOPE['target']}")
    print(f"Type:            {SCOPE['target_type']}")
    print(f"Sensitivity:     {SCOPE['sensitivity']}")
    print(f"Authorized by:   {SCOPE['authorization']['authorized_by']}")
    print(f"Date:            {SCOPE['authorization']['authorization_date']}")
    print(f"\nIn Scope:")
    for item in SCOPE['in_scope']:
        print(f"  ✓ {item}")
    print(f"\nOut of Scope:")
    for item in SCOPE['out_of_scope']:
        print(f"  ✗ {item}")
    print(f"\nObjectives:")
    for obj in SCOPE['objectives']:
        print(f"  → {obj}")
    print("="*70 + "\n")

def ai_guided_pentest():
    """Main AI-guided penetration testing function"""
    
    # Display scope
    print_scope_summary()
    
    # Verify scope
    in_scope, msg = check_scope(SCOPE['target'])
    if not in_scope:
        print(f"❌ {msg}")
        print("Aborting test - target not in scope!")
        return
    
    print(f"✓ {msg}\n")
    
    # Initialize report
    report = {
        "target": SCOPE['target'],
        "start_time": datetime.now().isoformat(),
        "scope": SCOPE,
        "phases": []
    }
    
    target = SCOPE['target']
    
    # Phase 1: AI Strategy Planning
    print("\n" + "="*70)
    print("PHASE 1: AI STRATEGY PLANNING")
    print("="*70 + "\n")
    
    planning_prompt = f"""As a penetration testing expert, create a testing strategy for:

Target: {target}
Type: {SCOPE['target_type']}
Sensitivity: {SCOPE['sensitivity']}

Available tools: {', '.join(SCOPE['constraints']['allowed_tools'])}

Objectives:
{chr(10).join('- ' + obj for obj in SCOPE['objectives'])}

Provide EXACTLY 4 specific testing steps. Format each as:
Step X: [tool_name] - [specific_command_flags] - [reason]

Example:
Step 1: whatweb - -a 3 {target} - Identify web technologies and frameworks
Step 2: subfinder - -d {target} -silent - Discover subdomains

Be concise and specific."""

    print("[AI] 🤖 Planning reconnaissance strategy...")
    strategy = ask_ollama(planning_prompt)
    print(f"\n[AI] Strategy:\n{'-'*70}\n{strategy}\n{'-'*70}\n")
    
    report['phases'].append({
        "phase": "planning",
        "strategy": strategy,
        "timestamp": datetime.now().isoformat()
    })
    
    # Parse strategy to extract steps
    steps = []
    for line in strategy.split('\n'):
        if line.strip().startswith(('Step', '1.', '2.', '3.', '4.')):
            steps.append(line.strip())
    
    print(f"[*] Identified {len(steps)} testing steps\n")
    
    # Phase 2: Execute Reconnaissance
    print("\n" + "="*70)
    print("PHASE 2: RECONNAISSANCE")
    print("="*70 + "\n")
    
    phase_results = []
    
    # Execute first few commands
    commands_to_run = [
        ("whatweb", f"whatweb https://{target} -a 3", "Technology Detection"),
        ("httpx", f"echo https://{target} | httpx -status-code -tech-detect -title", "HTTP Probe"),
        ("subfinder", f"subfinder -d {target} -silent", "Subdomain Discovery"),
    ]
    
    for tool, cmd, desc in commands_to_run:
        # Check if tool is allowed
        allowed, msg = check_tool_allowed(tool)
        if not allowed:
            print(f"⚠️  Skipping: {msg}\n")
            continue
        
        success, output = execute_Hexstrike_command(cmd, desc)
        
        if success:
            print(f"✓ Success (first 500 chars):")
            print(f"{output[:500]}\n")
            phase_results.append({
                "tool": tool,
                "command": cmd,
                "success": True,
                "output": output[:1000]  # Store first 1000 chars
            })
        else:
            print(f"✗ Failed: {output}\n")
            phase_results.append({
                "tool": tool,
                "command": cmd,
                "success": False,
                "error": output
            })
        
        time.sleep(2)  # Rate limiting
    
    report['phases'].append({
        "phase": "reconnaissance",
        "results": phase_results,
        "timestamp": datetime.now().isoformat()
    })
    
    # Phase 3: AI Analysis & Recommendations
    print("\n" + "="*70)
    print("PHASE 3: AI ANALYSIS")
    print("="*70 + "\n")
    
    # Combine results for AI analysis
    results_summary = "\n".join([
        f"{r['tool']}: {'Success' if r['success'] else 'Failed'}\n{r.get('output', r.get('error', ''))[:300]}"
        for r in phase_results
    ])
    
    analysis_prompt = f"""Analyze these penetration test results:

{results_summary}

Based on the findings:
1. Identify 2-3 key security findings
2. Recommend the next 2 testing actions (be specific with tools and targets)
3. Rate overall security posture (Low/Medium/High risk)

Be concise and actionable."""

    print("[AI] 🤖 Analyzing results...")
    analysis = ask_ollama(analysis_prompt, context="You are analyzing real penetration test results.")
    print(f"\n[AI] Analysis:\n{'-'*70}\n{analysis}\n{'-'*70}\n")
    
    report['phases'].append({
        "phase": "analysis",
        "analysis": analysis,
        "timestamp": datetime.now().isoformat()
    })
    
    # Phase 4: Vulnerability Scanning (if in objectives)
    if "vulnerability_scanning" in SCOPE['objectives']:
        print("\n" + "="*70)
        print("PHASE 4: VULNERABILITY SCANNING")
        print("="*70 + "\n")
        
        vuln_cmd = f"nuclei -u https://{target} -severity critical,high,medium -silent"
        success, output = execute_Hexstrike_command(vuln_cmd, "Nuclei Vulnerability Scan")
        
        if success and output.strip():
            print(f"⚠️  Vulnerabilities Found:\n{output[:800]}\n")
            
            # Ask AI to prioritize vulnerabilities
            vuln_analysis_prompt = f"""Analyze these vulnerability scan results:

{output[:1000]}

Provide:
1. Top 3 most critical findings
2. Exploitation difficulty for each
3. Recommended remediation priority

Be specific and practical."""
            
            print("[AI] 🤖 Prioritizing vulnerabilities...")
            vuln_analysis = ask_ollama(vuln_analysis_prompt)
            print(f"\n[AI] Vulnerability Analysis:\n{'-'*70}\n{vuln_analysis}\n{'-'*70}\n")
            
            report['phases'].append({
                "phase": "vulnerability_scanning",
                "raw_output": output[:2000],
                "ai_analysis": vuln_analysis,
                "timestamp": datetime.now().isoformat()
            })
        else:
            print("✓ No critical/high/medium vulnerabilities detected\n")
    
    # Final Report
    report['end_time'] = datetime.now().isoformat()
    report['status'] = 'completed'
    
    # Save report
    filename = f"pentest_report_{SCOPE['target'].replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    print("\n" + "="*70)
    print("PENETRATION TEST COMPLETE")
    print("="*70)
    print(f"✓ Report saved: {filename}")
    print(f"✓ Duration: {report['end_time']}")
    print("\nAI-powered penetration test completed successfully! 🎉")

if __name__ == "__main__":
    try:
        ai_guided_pentest()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
