#!/usr/bin/env python3
"""Test script for RAVEN config loader."""

import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tests'))

from raven.utils.config_loader import load_config, ProviderConfig, AgentConfig, TeamConfig

print('=== Config Loader Tests ===')

# Test ProviderConfig with a specific provider
config = load_config('configs/providers.yaml', ProviderConfig)
print(f'ProviderConfig loaded: {config}')

# Test AgentConfig
data = {
    'provider': 'openai',
    'model': 'gpt-4o',
    'role': 'developer',
    'instructions': 'Write clean code.',
}
agent_config = AgentConfig(**data)
print(f'AgentConfig: provider={agent_config.provider}, model={agent_config.model}, role={agent_config.role}, instructions={agent_config.instructions}')

# Test TeamConfig
team_config = TeamConfig(num_agents=3)
print(f'TeamConfig num_agents={team_config.num_agents}')

# Test team size validation
try:
    TeamConfig(num_agents=1)
    print('ERROR: TeamConfig(num_agents=1) should have raised')
except Exception as e:
    print(f'TeamConfig(num_agents=1) raised: {type(e).__name__}')

team_config_5 = TeamConfig(num_agents=5)
print(f'TeamConfig(num_agents=5) = {team_config_5.num_agents}')

team_config_2 = TeamConfig(num_agents=2)
print(f'TeamConfig(num_agents=2) = {team_config_2.num_agents}')

team_config_4 = TeamConfig(num_agents=4)
print(f'TeamConfig(num_agents=4) = {team_config_4.num_agents}')

print()
print('All config tests passed!')