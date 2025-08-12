from app.core.dasboard_ws import dashboard_ws_manager

async def trigger_agent_update(agent_count: int, user_id: str, org_id: str):
    stats = {
        "agent_count": agent_count,
        "org_id": org_id
    } 
    await dashboard_ws_manager.send_user_stats(user_id, stats)
    await dashboard_ws_manager.broadcast_org_stats(org_id, stats)
    
async def trigger_conversation_update(conversation_count: int, user_id: str, org_id: str):
    stats = {
        "conversation_count": conversation_count,
        "org_id": org_id
    }
    await dashboard_ws_manager.send_user_stats(user_id, stats)
    await dashboard_ws_manager.broadcast_org_stats(org_id, stats)

async def trigger_kb_update(kb_count: int, org_id: str):
    stats = {
        "kb_count": kb_count,
        "org_id": org_id
    }
    await dashboard_ws_manager.broadcast_org_stats(org_id, stats)