use std::process::Command;

// تولید و اجرای قوانین kill-switch سطح کرنل (iptables).
// Generation and execution of kernel-level kill-switch rules (iptables).

#[derive(Debug)]
#[allow(dead_code)]
pub enum FirewallBackend {
    Iptables,
    #[allow(dead_code)]
    Nftables,
}

#[derive(Debug)]
#[allow(dead_code)]
pub struct KillSwitchRuleset {
    #[allow(dead_code)]
    pub backend: FirewallBackend,
    pub rules: Vec<String>,
}

pub trait RuleExecutor {
    fn execute(&self, command: &str) -> Result<(), String>;
}

pub struct IptablesExecutor;

impl RuleExecutor for IptablesExecutor {
    fn execute(&self, command: &str) -> Result<(), String> {
        let parts: Vec<&str> = command.split_whitespace().collect();
        if parts.is_empty() {
            return Ok(());
        }
        let status = Command::new(parts[0])
            .args(&parts[1..])
            .status()
            .map_err(|e| format!("failed to execute '{}': {}", command, e))?;
        if status.success() {
            Ok(())
        } else {
            Err(format!("command '{}' exited with non-zero status", command))
        }
    }
}

// یک تست واقعی نوشتن/حذف قانون برای تشخیص قابلیت واقعی کرنل.
// A real write/delete rule probe to detect actual kernel capability.
pub fn probe_kernel_capability() -> bool {
    let probe_add = "iptables -t mangle -I OUTPUT 1 -p tcp --dport 65535 -j DROP";
    let probe_del = "iptables -t mangle -D OUTPUT 1 -p tcp --dport 65535 -j DROP";

    let executor = IptablesExecutor;
    if executor.execute(probe_add).is_err() {
        return false;
    }
    let _ = executor.execute(probe_del);
    true
}

// قوانین kill-switch را برای یک رابط شبکه و UID پروسه‌ی xray-core می‌سازد.
// Builds kill-switch rules for a network interface and xray-core process UID.
// NOTE: xray_uid is now REQUIRED. Without it, the rules would block xray-core's
// own tunnel traffic, breaking the connection — this was a real bug.
pub fn build_killswitch_rules(
    interface: &str,
    xray_uid: Option<u32>,
) -> Result<KillSwitchRuleset, String> {
    let uid = xray_uid.ok_or_else(|| {
        "xray_uid is required: without it, kill-switch would block xray-core's own tunnel traffic, breaking the connection".to_string()
    })?;

    let mut rules = Vec::new();

    rules.push(format!(
        "iptables -t filter -I OUTPUT -o {} -m owner ! --uid-owner {} -j DROP",
        interface, uid
    ));
    rules.push(format!(
        "iptables -t filter -I INPUT -i {} -m owner ! --uid-owner {} -j DROP",
        interface, uid
    ));

    Ok(KillSwitchRuleset {
        backend: FirewallBackend::Iptables,
        rules,
    })
}

// قوانین را با یک executor اجرا می‌کند.
// Executes the rules with a given executor.
pub fn apply_ruleset(
    ruleset: &KillSwitchRuleset,
    executor: &dyn RuleExecutor,
) -> Result<(), String> {
    for rule in &ruleset.rules {
        executor.execute(rule)?;
    }
    Ok(())
}

// قوانین را برعکس اجرا می‌کند (حذف).
// Reverses the rules (deletes them).
pub fn remove_ruleset(
    ruleset: &KillSwitchRuleset,
    executor: &dyn RuleExecutor,
) -> Result<(), String> {
    for rule in ruleset.rules.iter().rev() {
        let delete_rule = rule.replace(" -I ", " -D ");
        executor.execute(&delete_rule)?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    pub struct MockExecutor {
        pub executed_commands: std::sync::Mutex<Vec<String>>,
    }

    impl RuleExecutor for MockExecutor {
        fn execute(&self, command: &str) -> Result<(), String> {
            self.executed_commands.lock().unwrap().push(command.to_string());
            Ok(())
        }
    }

    #[test]
    fn probe_kernel_capability_does_not_panic() {
        let _ = probe_kernel_capability();
    }

    #[test]
    fn build_ruleset_with_uid_includes_owner_match() {
        let ruleset = build_killswitch_rules("eth0", Some(1000)).unwrap();
        assert_eq!(ruleset.rules.len(), 2);
        assert!(ruleset.rules[0].contains("eth0"));
        assert!(ruleset.rules[0].contains("1000"));
        assert!(ruleset.rules[0].contains("-m owner ! --uid-owner"));
    }

    #[test]
    fn build_ruleset_without_uid_returns_error() {
        let result = build_killswitch_rules("eth0", None);
        assert!(result.is_err());
        let msg = result.unwrap_err();
        assert!(msg.contains("xray_uid is required"), "unexpected error: {msg}");
    }

    #[test]
    fn mock_executor_records_commands() {
        let executor = MockExecutor {
            executed_commands: std::sync::Mutex::new(Vec::new()),
        };
        let ruleset = build_killswitch_rules("wlan0", Some(9999)).unwrap();
        apply_ruleset(&ruleset, &executor).unwrap();
        let cmds = executor.executed_commands.lock().unwrap();
        assert_eq!(cmds.len(), 2);
        assert!(cmds[0].contains("wlan0"));
        assert!(cmds[0].contains("9999"));
    }

    #[test]
    fn remove_ruleset_reverses_insert_to_delete() {
        let executor = MockExecutor {
            executed_commands: std::sync::Mutex::new(Vec::new()),
        };
        let ruleset = build_killswitch_rules("eth0", Some(1000)).unwrap();
        remove_ruleset(&ruleset, &executor).unwrap();
        let cmds = executor.executed_commands.lock().unwrap();
        assert_eq!(cmds.len(), 2);
        assert!(cmds[0].contains(" -D "));
        assert!(cmds[1].contains(" -D "));
    }

    // تست integration-level: کل مسیر build → apply با UID واقعی.
    // Integration-level test: full build → apply path with a real UID.
    #[test]
    fn full_path_with_uid_exempts_xray_traffic() {
        let executor = MockExecutor {
            executed_commands: std::sync::Mutex::new(Vec::new()),
        };

        let ruleset = build_killswitch_rules("eth0", Some(1000)).unwrap();
        apply_ruleset(&ruleset, &executor).unwrap();

        let cmds = executor.executed_commands.lock().unwrap();
        assert_eq!(cmds.len(), 2);

        // هر دو قانون باید شامل استثنای UID باشند تا ترافیک xray-core مسدود نشود.
        // Both rules must include the UID exemption so xray-core traffic is not blocked.
        for cmd in cmds.iter() {
            assert!(
                cmd.contains("-m owner ! --uid-owner 1000"),
                "rule must exempt xray-core UID to avoid blocking its own tunnel: {cmd}"
            );
        }
    }

    // تست integration-level: حذف قوانین برعکس اعمال می‌شود.
    // Integration-level test: rules are removed in reverse order.
    #[test]
    fn full_path_remove_reverses_application_order() {
        let executor = MockExecutor {
            executed_commands: std::sync::Mutex::new(Vec::new()),
        };

        let ruleset = build_killswitch_rules("eth0", Some(1000)).unwrap();
        apply_ruleset(&ruleset, &executor).unwrap();
        let applied = executor.executed_commands.lock().unwrap().clone();

        let executor2 = MockExecutor {
            executed_commands: std::sync::Mutex::new(Vec::new()),
        };
        remove_ruleset(&ruleset, &executor2).unwrap();
        let removed = executor2.executed_commands.lock().unwrap();

        assert_eq!(removed.len(), 2);
        // ترتیب حذف باید برعکس ترتیب اعمال باشد.
        // Removal order must be reverse of application order.
        assert_eq!(applied[0].replace(" -I ", " -D "), removed[1]);
        assert_eq!(applied[1].replace(" -I ", " -D "), removed[0]);
    }
}
