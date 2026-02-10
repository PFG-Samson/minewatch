
# Alert Rules API Endpoints

@app.get("/alert-rules")
def get_alert_rules() -> dict[str, Any]:
    """Get current alert rule configuration"""
    from backend.alert_rules import AlertRuleEngine
    
    engine = AlertRuleEngine()
    return engine.get_config()


class AlertRulesUpdate(BaseModel):
    """Model for updating alert rules configuration"""
    rules: dict[str, Any]
    global_settings: Optional[dict[str, Any]] = None


@app.put("/alert-rules")
def update_alert_rules(payload: AlertRulesUpdate) -> dict[str, str]:
    """
    Update alert rule configuration.
    
    This endpoint allows administrators to modify alert thresholds,
    enable/disable specific rules, and adjust severity levels.
    """
    from backend.alert_rules import AlertRuleEngine
    
    engine = AlertRuleEngine()
    
    # Build new config
    new_config = {
        "version": "1.0",
        "rules": payload.rules
    }
    
    if payload.global_settings:
        new_config["global_settings"] = payload.global_settings
    
    # Update and reload
    engine.update_config(new_config)
    
    return {"status": "success", "message": "Alert rules updated successfully"}
