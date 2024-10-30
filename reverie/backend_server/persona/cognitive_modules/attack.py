import datetime
import random
from persona.prompt_template.gpt_structure import *
from persona.cognitive_modules.retrieve import *
from persona.prompt_template.run_gpt_prompt import (
    run_gpt_prompt_attack_summarize_ideas,
    run_gpt_prompt_attack_summarize_relationship,
    run_gpt_prompt_generate_attack,
    run_gpt_prompt_attack_poignancy,
    run_gpt_prompt_decide_to_attack,
    run_gpt_prompt_decide_attack_reaction,
    run_gpt_prompt_generate_attack_action
)

def generate_attack_summarize_ideas(init_persona, target_persona, retrieved, curr_context):
    all_embedding_keys = [i.embedding_key for val in retrieved.values() for i in val]
    all_embedding_key_str = "\n".join(all_embedding_keys)

    try:
        summarized_idea = run_gpt_prompt_attack_summarize_ideas(init_persona,
                            target_persona, all_embedding_key_str, 
                            curr_context)[0]
    except:
        summarized_idea = ""
    return summarized_idea

def generate_summarize_attack_relationship(init_persona, target_persona, retrieved):
    all_embedding_keys = [i.embedding_key for val in retrieved.values() for i in val]
    all_embedding_key_str = "\n".join(all_embedding_keys)

    summarized_relationship = run_gpt_prompt_attack_summarize_relationship(
                                init_persona, target_persona,
                                all_embedding_key_str)[0]
    return summarized_relationship

def generate_attack(maze, init_persona, target_persona, curr_context, init_summ_idea, target_summ_idea):
    attack_details = run_gpt_prompt_generate_attack(maze, 
                                                    init_persona, 
                                                    target_persona,
                                                    curr_context, 
                                                    init_summ_idea, 
                                                    target_summ_idea)[0]
    return attack_details

def agent_attack(maze, init_persona, target_persona):
    curr_context = (f"{init_persona.scratch.name} " + 
                f"was {init_persona.scratch.act_description} " + 
                f"when {init_persona.scratch.name} " + 
                f"saw {target_persona.scratch.name} " + 
                f"in the middle of {target_persona.scratch.act_description}.\n")
    curr_context += (f"{init_persona.scratch.name} " +
                f"is considering attacking " +
                f"{target_persona.scratch.name}.")

    summarized_ideas = []
    part_pairs = [(init_persona, target_persona), 
                  (target_persona, init_persona)]
    for p_1, p_2 in part_pairs:
        focal_points = [f"{p_2.scratch.name}"]
        retrieved = new_retrieve(p_1, focal_points, 50)
        relationship = generate_summarize_attack_relationship(p_1, p_2, retrieved)
        focal_points = [f"{relationship}", 
                        f"{p_2.scratch.name} is {p_2.scratch.act_description}"]
        retrieved = new_retrieve(p_1, focal_points, 25)
        summarized_idea = generate_attack_summarize_ideas(p_1, p_2, retrieved, curr_context)
        summarized_ideas.append(summarized_idea)

    return generate_attack(maze, init_persona, target_persona, 
                        curr_context, 
                        summarized_ideas[0], 
                        summarized_ideas[1])

def generate_attack_poignancy(persona, attack_description):
    attack_poignancy = run_gpt_prompt_attack_poignancy(persona, attack_description)[0]
    return attack_poignancy

def add_attack_to_memory(persona, target_persona, attack_details):
    created = persona.scratch.curr_time
    expiration = persona.scratch.curr_time + datetime.timedelta(days=30)
    s, p, o = (persona.name, "attacks", target_persona.name)
    keywords = set([s, p, o, "attack", "violence"])
    attack_poignancy = generate_attack_poignancy(persona, attack_details["description"])
    attack_embedding_pair = (attack_details["description"], get_embedding(attack_details["description"]))
    
    persona.a_mem.add_event(created, expiration, s, p, o, 
                            attack_details["description"], keywords, attack_poignancy, 
                            attack_embedding_pair, None)

def process_attack(maze, init_persona, target_persona):
    # Step 1: Retrieve memories
    focal_points = [f"{target_persona.name}", "attack", "violence"]
    retrieved = new_retrieve(init_persona, focal_points, 25)
    
    # Step 2: Decide to attack
    attack_decision = run_gpt_prompt_decide_to_attack(init_persona, target_persona, retrieved)[0]
    
    if attack_decision == "yes":
        while True:
            # Generate attack action
            attack_action, = run_gpt_prompt_generate_attack_action(init_persona, target_persona)[0]
            
            # Update health based on attack action
            damage = calculate_damage(init_persona, target_persona, attack_action)
            adjust_health(target_persona, damage)
            
            # Add attack to memory
            attack_details = {
                "description": attack_action,
                "damage": damage
            }
            add_attack_to_memory(init_persona, target_persona, attack_details)
            
            if target_persona.scratch.health <= 0:
                return f"{target_persona.name} has been defeated."
            
            # Retrieve target's memories before deciding reaction
            target_retrieved = new_retrieve(target_persona, 
                                         [f"{init_persona.name}", "attack", "violence"], 
                                         25)
            
            # Decide target's reaction with retrieved memories
            reaction = run_gpt_prompt_decide_attack_reaction(target_persona, 
                                                           init_persona, 
                                                           attack_action,
                                                           target_retrieved)[0]
            
            if reaction == "flee":
                return f"{target_persona.name} has fled from the attack."
            
            # If target decides to attack back, swap roles and continue the loop
            init_persona, target_persona = target_persona, init_persona
            # Also swap retrieved memories
            retrieved = target_retrieved
    
    return "No attack occurred."

def calculate_damage(attacker, defender, attack_action):
    # 简单的伤害计算,可以根据需要进行调整
    base_damage = attacker.scratch.attack_power
    # 可以根据 attack_action 的描述来调整伤害
    return base_damage

def adjust_health(persona, damage):
    persona.scratch.health = max(persona.scratch.health - damage, 0)
    return persona.scratch.health
