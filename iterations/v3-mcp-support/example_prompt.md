Use meta_agent mcp and ask the Meta Agent agent.
Is this the right pydantic agent intialization?
async def finish_conversation(state: AgentState, writer):
    log_node("Finish Conversation", "Ending conversation and providing instructions")
    
    # Get the message history into the format for Pydantic AI
    message_history: list[ModelMessage] = []
    for message_row in state['messages']:
        message_history.extend(ModelMessagesTypeAdapter.validate_json(message_row))
    log_info(f"Loaded {len(message_history)} messages for final response")

    # Run the agent in a stream
    log_agent("End Conversation", "Generating farewell message and instructions...")
    if is_ollama:
        writer = get_stream_writer()
        result = await end_conversation_agent.run(state['latest_user_message'], message_history= message_history)
        writer(result.data)
        log_success("End conversation message generated (Ollama mode)")
    else: 
        async with end_conversation_agent.run_stream(
            state['latest_user_message'],
            message_history= message_history
        ) as result:
            # Stream partial text as it arrives
            async for chunk in result.stream_text(delta=True):
                writer(chunk)
        log_success("End conversation message streamed (OpenAI mode)")

    log_state("Conversation ended, updating final state")
    return {"messages": [result.new_messages_json()]}       