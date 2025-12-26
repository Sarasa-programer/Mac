# Deployment Strategy: Independent Version Migration

## Overview

This document outlines the deployment strategy for migrating from Groq-based models to independent providers (OpenRouter/Qwen, OpenAI/Whisper) while maintaining zero downtime and ensuring rollback capability.

## Deployment Architecture

### Blue-Green Deployment Pattern

```
┌─────────────────┐         ┌─────────────────┐
│   Load Balancer │────────▶│  Current (Groq) │
└─────────────────┘         └─────────────────┘
                                      │
                                      │ Gradual Traffic Shift
                                      ▼
                            ┌─────────────────┐
                            │ Independent     │
                            │ (OpenRouter/    │
                            │  OpenAI)        │
                            └─────────────────┘
```

### Traffic Routing Strategy

1. **Phase 1: Canary Deployment (10% traffic)**
   - Route 10% of traffic to independent version
   - Monitor error rates, latency, and accuracy
   - Duration: 24-48 hours

2. **Phase 2: Gradual Increase (25%, 50%, 75%)**
   - Increase traffic share gradually
   - Monitor at each stage
   - Duration: 1-2 days per stage

3. **Phase 3: Full Cutover (100%)**
   - Route all traffic to independent version
   - Keep Groq version available for 1 week
   - Duration: 1 week

4. **Phase 4: Deprecation**
   - Remove Groq dependencies
   - Clean up legacy code
   - Duration: 1-2 days

## Pre-Deployment Checklist

### Configuration

- [ ] All API keys configured and validated
- [ ] Feature flags set appropriately
- [ ] Fallback chain configured
- [ ] Environment variables documented
- [ ] Configuration files reviewed

### Testing

- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] Load tests completed
- [ ] A/B testing framework validated
- [ ] Error scenarios tested

### Monitoring

- [ ] Metrics collection configured
- [ ] Alerting rules defined
- [ ] Dashboards created
- [ ] Log aggregation set up
- [ ] Cost monitoring enabled

### Rollback Plan

- [ ] Rollback procedures documented
- [ ] Quick rollback scripts prepared
- [ ] Data migration scripts tested
- [ ] Communication plan ready

## Deployment Steps

### Step 1: Staging Deployment

```bash
# Deploy to staging environment
git checkout independent
git pull origin independent

# Set environment variables
export PRIMARY_PROVIDER=openrouter
export PRIMARY_STT_PROVIDER=openai
export ENABLE_GROQ=true  # Keep as fallback
export ENABLE_FALLBACK=true

# Run migrations (if any)
python scripts/migrate_config.py

# Start services
docker-compose up -d

# Verify deployment
./scripts/health_check.sh
```

### Step 2: Monitoring Setup

```bash
# Start monitoring services
docker-compose -f docker-compose.monitoring.yml up -d

# Verify metrics collection
curl http://localhost:9090/metrics

# Check logs
docker-compose logs -f app
```

### Step 3: Canary Deployment (Production)

```bash
# Update load balancer config (10% to new version)
kubectl apply -f k8s/canary-10-percent.yaml

# Monitor for 24 hours
watch -n 60 './scripts/check_metrics.sh'

# Review metrics
# - Error rate < 1%
# - P95 latency < 2s
# - Success rate > 99%
```

### Step 4: Gradual Rollout

```bash
# Increase to 25%
kubectl apply -f k8s/canary-25-percent.yaml
# Monitor for 12 hours

# Increase to 50%
kubectl apply -f k8s/canary-50-percent.yaml
# Monitor for 12 hours

# Increase to 75%
kubectl apply -f k8s/canary-75-percent.yaml
# Monitor for 24 hours
```

### Step 5: Full Cutover

```bash
# Route 100% traffic to independent version
kubectl apply -f k8s/full-cutover.yaml

# Disable Groq (keep as emergency fallback)
export ENABLE_GROQ=false
kubectl rollout restart deployment/app

# Monitor for 1 week
```

### Step 6: Deprecation

```bash
# Remove Groq dependencies
git rm -r src/infrastructure/ai/groq*
git rm -r app/services/groq*

# Update configuration
# Remove GROQ_API_KEY from .env
# Remove groq references from config files

# Commit and deploy
git commit -m "Remove Groq dependencies"
git push origin independent
```

## Monitoring Metrics

### Key Performance Indicators (KPIs)

1. **Availability**
   - Target: 99.9% uptime
   - Measurement: Uptime percentage per day

2. **Latency**
   - Transcription: P95 < 2s
   - Analysis: P95 < 5s
   - Target: < 3s average

3. **Error Rate**
   - Target: < 0.1%
   - Measurement: (Errors / Total Requests) * 100

4. **Cost**
   - Target: < $X per 1000 requests
   - Measurement: Daily API costs

5. **Accuracy** (if applicable)
   - Transcription accuracy: > 95%
   - Analysis quality: Maintained or improved

### Metrics to Monitor

#### Provider-Level Metrics

```
- provider_request_count{provider="openrouter",status="success"}
- provider_request_count{provider="openrouter",status="error"}
- provider_latency_seconds{provider="openrouter",quantile="0.95"}
- provider_fallback_count{from="openrouter",to="groq"}
```

#### Service-Level Metrics

```
- transcription_requests_total
- transcription_success_rate
- transcription_latency_seconds
- analysis_requests_total
- analysis_success_rate
- analysis_latency_seconds
```

#### Cost Metrics

```
- api_cost_dollars{provider="openrouter"}
- api_cost_dollars{provider="openai"}
- tokens_used_total{provider="openrouter"}
```

## Alerting Rules

### Critical Alerts (Page on-call)

1. **High Error Rate**
   - Condition: Error rate > 5% for 5 minutes
   - Action: Page on-call engineer

2. **Service Down**
   - Condition: Health check failing for 2 minutes
   - Action: Page on-call engineer

3. **Cost Spike**
   - Condition: Daily cost > 150% of baseline
   - Action: Page on-call engineer

### Warning Alerts (Email/Slack)

1. **Elevated Error Rate**
   - Condition: Error rate > 1% for 15 minutes
   - Action: Send notification

2. **High Latency**
   - Condition: P95 latency > 5s for 10 minutes
   - Action: Send notification

3. **Provider Rate Limiting**
   - Condition: 429 errors detected
   - Action: Send notification, check fallback

## Rollback Procedures

### Quick Rollback (Feature Flag)

If issues are detected, rollback using feature flags:

```bash
# Immediate rollback to Groq
export PRIMARY_PROVIDER=groq
export ENABLE_GROQ=true
kubectl rollout restart deployment/app

# Or update load balancer to route 100% to Groq version
kubectl apply -f k8s/rollback-to-groq.yaml
```

### Full Rollback (Code)

If feature flag rollback doesn't work:

```bash
# Revert to previous version
git checkout v1.0-groq-baseline
git push origin main --force

# Redeploy
kubectl rollout undo deployment/app

# Or
docker-compose down
docker-compose up -d
```

### Data Migration Rollback

If data migration is needed:

```bash
# Run rollback migration script
python scripts/rollback_migration.py

# Verify data integrity
python scripts/verify_data_integrity.py
```

## Communication Plan

### Stakeholder Updates

1. **Pre-Deployment**
   - Notify stakeholders 1 week before
   - Share deployment schedule
   - Request maintenance window if needed

2. **During Deployment**
   - Send status updates every 4 hours
   - Notify on any issues
   - Share metrics dashboard

3. **Post-Deployment**
   - Send summary report after 24 hours
   - Share performance metrics
   - Document any issues and resolutions

### User Communication

1. **Maintenance Window** (if needed)
   - Email users 48 hours before
   - Display banner in application
   - Post on status page

2. **Feature Changes**
   - Document any user-facing changes
   - Update user documentation
   - Provide migration guide if needed

## Post-Deployment Validation

### Week 1: Intensive Monitoring

- [ ] Monitor error rates daily
- [ ] Review latency metrics daily
- [ ] Check cost tracking daily
- [ ] Validate accuracy (if applicable)
- [ ] Review user feedback

### Week 2-4: Stable Monitoring

- [ ] Weekly performance reviews
- [ ] Cost analysis
- [ ] User satisfaction surveys
- [ ] Optimization opportunities

### Month 2+: Optimization

- [ ] Performance tuning
- [ ] Cost optimization
- [ ] Feature enhancements
- [ ] Documentation updates

## Success Criteria

Deployment is considered successful when:

1. ✅ All traffic routed to independent version
2. ✅ Error rate < 0.1% for 1 week
3. ✅ Latency within acceptable range
4. ✅ Cost within budget
5. ✅ No user complaints
6. ✅ All tests passing
7. ✅ Documentation updated

## Risk Mitigation

### Identified Risks

1. **API Rate Limiting**
   - Mitigation: Implement queuing and retry logic
   - Fallback: Use alternative providers

2. **Cost Overruns**
   - Mitigation: Set budget alerts
   - Fallback: Implement rate limiting

3. **Performance Degradation**
   - Mitigation: Load testing before deployment
   - Fallback: Rollback to Groq

4. **Data Loss**
   - Mitigation: Backup before migration
   - Fallback: Data restoration procedures

## Appendix

### Useful Commands

```bash
# Check deployment status
kubectl get deployments
kubectl get pods

# View logs
kubectl logs -f deployment/app

# Check metrics
curl http://localhost:9090/metrics | grep provider

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/cases/test

# Cost tracking
python scripts/cost_tracker.py --period daily
```

### Emergency Contacts

- On-call Engineer: [Contact Info]
- DevOps Team: [Contact Info]
- Product Owner: [Contact Info]

### Related Documentation

- [MIGRATION_PLAN.md](./MIGRATION_PLAN.md)
- [docs/MIGRATION_GUIDE.md](./docs/MIGRATION_GUIDE.md)
- [ARCHITECTURE.md](./ARCHITECTURE.md)

