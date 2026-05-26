const cds = require('@sap/cds')
module.exports = cds.service.impl(async function () {
  const db = await cds.connect.to('db')
  this.on('READ', 'Assets', (req) => {
    const key = req.data?.ASSET_ID
    if (key) return db.run(`SELECT * FROM "ASSET_MASTER"."ASSETS" WHERE "ASSET_ID" = ?`, [key])
    return db.run('SELECT * FROM "ASSET_MASTER"."ASSETS"')
  })
  this.on('READ', 'SensorReadings',    () => db.run('SELECT * FROM "IOT_SENSOR"."SENSOR_READINGS"'))
  this.on('READ', 'WorkOrders',        () => db.run('SELECT * FROM "EAM_PM"."WORK_ORDERS"'))
  this.on('READ', 'FailureHistory',    () => db.run('SELECT * FROM "EAM_PM"."FAILURE_HISTORY"'))
  this.on('READ', 'ProcessTrends',     () => db.run('SELECT * FROM "SCADA_OSIPI"."PROCESS_TRENDS"'))
  this.on('READ', 'ComplianceDocs',    () => db.run('SELECT * FROM "COMPLIANCE_QM"."COMPLIANCE_DOCS"'))
  this.on('READ', 'Inspections',       () => db.run('SELECT * FROM "COMPLIANCE_QM"."INSPECTIONS"'))
  this.on('READ', 'AssetHealthScores', () => db.run('SELECT * FROM "ASSET_MASTER"."ASSET_HEALTH_SCORES"'))
  this.on('READ', 'HealthScores',      () => db.run('SELECT * FROM "ASSET_MASTER"."ASSET_HEALTH_SCORES"'))
  this.on('READ', 'Thresholds',        () => db.run('SELECT * FROM "ASSET_MASTER"."ASSET_THRESHOLDS"'))
  this.on('READ', 'Financials',        () => db.run('SELECT * FROM "ASSET_MASTER"."ASSET_FINANCIALS"'))
  this.on('askAI', async (req) => {
    const { question } = req.data
    try {
      //const assets = await db.run('SELECT ASSET_ID, STATUS, HEALTH_SCORE, FAILURE_PROB, RUL_DAYS FROM "ASSET_MASTER"."ASSET_HEALTH_SCORES" ORDER BY HEALTH_SCORE ASC LIMIT 5')
      const assets = await db.run('SELECT ASSET_ID, STATUS, HEALTH_SCORE, FAILURE_PROB, RUL_DAYS FROM "ASSET_MASTER"."ASSET_HEALTH_SCORES" ORDER BY ASSET_ID ASC')
      const context = assets.map(a => `${a.ASSET_ID}: health=${a.HEALTH_SCORE}, failure_prob=${a.FAILURE_PROB}, RUL=${a.RUL_DAYS} days, status=${a.STATUS}`).join('\n')
      const TOKEN_URL = 'https://bluwisdev-intelasset.authentication.us10.hana.ondemand.com/oauth/token'
      const CLIENT_ID = 'sb-7be1a8f8-1935-44b0-a0b1-00e0a083e2a6!b652584|aicore!b164'
      const CLIENT_SECRET = '8d8f90de-7496-4746-b29c-52aa1d81b11c$BsfMGfufLtl4Yl5OOZT0R1pDV3zxmZq-SAsHRpt74Ak='
      const AI_API_URL = 'https://api.ai.prod.us-east-1.aws.ml.hana.ondemand.com'
      const tokenRes = await fetch(TOKEN_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `grant_type=client_credentials&client_id=${encodeURIComponent(CLIENT_ID)}&client_secret=${encodeURIComponent(CLIENT_SECRET)}`
      })
      const { access_token } = await tokenRes.json()
      const aiRes = await fetch(`${AI_API_URL}/v2/inference/deployments/dfe36f91169ebcb0/completion`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${access_token}`, 'AI-Resource-Group': 'assetinteldev', 'Content-Type': 'application/json' },
        body: JSON.stringify({
          orchestration_config: {
            module_configurations: {
              templating_module_config: {
                template: [
                  { role: 'system', content: `You are an asset intelligence assistant for an oil & gas plant. Asset health data:\n${context}` },
                  { role: 'user', content: '{{?user_query}}' }
                ]
              },
              llm_module_config: {
                model_name: 'gpt-4o',
                model_params: { max_tokens: 500 }
              }
            }
          },
          input_params: { user_query: question }
        })
      })
      const aiData = await aiRes.json()
      const answer = aiData.module_results?.llm?.choices?.[0]?.message?.content
        || aiData.error?.message
        || JSON.stringify(aiData).substring(0, 300)
      return { answer }
    } catch (e) {
      console.error('askAI error:', e.message)
      return { answer: `Error: ${e.message}` }
    }
  })
})
