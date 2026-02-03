# Value Proposition Statement (VPS) Template

## Template Structure

The VPS follows a proven, structured format that ensures clarity and consistency:

```
Our [products/services] 
help(s) [customer segment] 
who [want to/need to] [jobs to be done] 
by [reducing/removing/avoiding] [pain] 
and [enabling/increasing] [gain], 
unlike [competing value proposition].
```

## Fixed vs Editable Elements

### Fixed Structural Elements (Cannot be changed)
These words provide the framework and must remain constant:

- **"Our"** - Possessive opening
- **"help(s)"** - Action verb connecting offering to customer
- **"who want to"** / **"who need to"** - Introduces customer's job-to-be-done
- **"by"** - Introduces the value delivery mechanism
- **"and"** - Connects pain relief to gain creation
- **"unlike"** - Introduces competitive differentiation

### Editable Content Fields (Populated by system, can be edited)

1. **[products/services]** - Auto-populated from Value Map
   - Source: VPC 2.0 → Value Map → Products & Services
   - Example: "on-demand video entertainment streaming service"
   - Example: "online ordering services"

2. **[customer segment]** - Auto-populated from Customer Profile
   - Source: VPC 2.0 → Customer Profile → Personas
   - Example: "viewers from all walks of life"
   - Example: "hungry people who don't want or can't cook"

3. **[jobs to be done]** - Auto-populated from Customer Profile
   - Source: VPC 2.0 → Customer Profile → Jobs-to-be-Done
   - Example: "watch video content conveniently and affordably"
   - Example: "eat their preferred meals conveniently"

4. **[pain relievers]** - Auto-populated from Value Map
   - Source: VPC 2.0 → Value Map → Pain Relievers
   - Must use action verbs: "reducing", "removing", "avoiding"
   - Example: "reducing the cost and inconveniences associated with watching movies and series"
   - Example: "removing the friction and frustration related to having a meal on the plate"

5. **[gain creators]** - Auto-populated from Value Map
   - Source: VPC 2.0 → Value Map → Gain Creators
   - Must use action verbs: "enabling", "increasing", "providing"
   - Example: "enabling on-demand access to millions of titles"
   - Example: "enabling access to an online food court with numerous meal options and delivery services"

6. **[competing value proposition]** - Auto-populated from market research
   - Source: Market Research Analysis → Competitive Analysis
   - Example: "TV channels and cinemas"
   - Example: "currently existing options"

## Real-World Examples

### Netflix VPS
```
Our on-demand video entertainment streaming service 
helps viewers from all walks of life 
who want to watch video content conveniently and affordably 
by reducing the cost and inconveniences associated with watching movies and series 
and enabling on-demand access to millions of titles, 
unlike TV channels and cinemas.
```

**Breakdown:**
- **Products/Services**: on-demand video entertainment streaming service
- **Customer Segment**: viewers from all walks of life
- **Jobs-to-be-Done**: watch video content conveniently and affordably
- **Pain Reliever**: reducing the cost and inconveniences associated with watching movies and series
- **Gain Creator**: enabling on-demand access to millions of titles
- **Competition**: TV channels and cinemas

### Vuba VPS
```
Our online ordering services 
help hungry people who don't want or can't cook 
who want to eat their preferred meals conveniently 
by removing the friction and frustration related to having a meal on the plate 
and enabling access to an online food court with numerous meal options and delivery services, 
unlike currently existing options.
```

**Breakdown:**
- **Products/Services**: online ordering services
- **Customer Segment**: hungry people who don't want or can't cook
- **Jobs-to-be-Done**: eat their preferred meals conveniently
- **Pain Reliever**: removing the friction and frustration related to having a meal on the plate
- **Gain Creator**: enabling access to an online food court with numerous meal options and delivery services
- **Competition**: currently existing options

## Action Verbs to Use

### For Pain Relievers (Choose one):
- **Reducing** - Making something less intense or severe
- **Removing** - Eliminating something completely
- **Avoiding** - Preventing something from happening

### For Gain Creators (Choose one):
- **Enabling** - Making something possible
- **Increasing** - Making something greater in amount or degree
- **Providing** - Supplying or making available

## Multi-Persona VPS

When the project has multiple personas, the VPS should:

1. **Use a broader customer segment** that encompasses both personas
   - Example: "farmers in rural Kenya" (includes both smallholder and commercial farmers)

2. **Address shared jobs-to-be-done** that apply to both personas
   - Example: "adapt to climate variability and improve productivity"

3. **Include pain relievers** that benefit both segments
   - Example: "reducing uncertainty from erratic weather patterns"

4. **Include gain creators** that create value for both
   - Example: "enabling data-driven agricultural decisions"

## System Implementation

### Auto-Population Logic

1. **Products/Services**: Extract from `vpc_data.value_map_selections.products_services`
2. **Customer Segment**: Combine from `personas` array, creating a unified description
3. **Jobs-to-be-Done**: Extract from `vpc_data.customer_profile.jobs_to_be_done`
4. **Pain Relievers**: Extract from `vpc_data.value_map_selections.pain_relievers`
5. **Gain Creators**: Extract from `vpc_data.value_map_selections.gain_creators`
6. **Competition**: Extract from `market_research_analysis` competitive insights

### Editing Workflow

1. **Initial Generation**: System auto-populates all fields from VPC 2.0 and market research
2. **Review**: User reviews the generated VPS
3. **Edit**: User can modify any of the editable content fields
4. **Fixed Structure**: The structural elements ("Our", "help(s)", "by", "and", "unlike") remain constant
5. **Save**: Updated VPS is saved with metadata tracking changes

## Best Practices

1. **Be Specific**: Use concrete, measurable language
   - ❌ "helps people who want convenience"
   - ✅ "helps busy professionals who want to save 2+ hours per week"

2. **Use Evidence**: Ground claims in validated research
   - ❌ "reducing costs"
   - ✅ "reducing costs by 40% compared to traditional alternatives"

3. **Stay Customer-Centric**: Focus on outcomes, not features
   - ❌ "providing a mobile app with GPS tracking"
   - ✅ "enabling real-time visibility and peace of mind"

4. **Be Memorable**: Make it clear and compelling
   - ❌ "Our solution helps customers achieve better results"
   - ✅ "Our AI-powered platform helps sales teams who want to close deals faster by removing manual data entry and enabling instant customer insights"

5. **Maintain Consistency**: Ensure alignment with VPC 2.0 data
   - All claims must be traceable to VPC elements or market research
   - Pain relievers must address documented pains
   - Gain creators must deliver documented gains
