# Formal Semantics of DeMoL (Device Modeling Language)

**A Mathematically Rigorous Specification**

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Mathematical Foundations](#2-mathematical-foundations)
   - 2.1 [Notation and Conventions](#21-notation-and-conventions)
   - 2.2 [Basic Structures](#22-basic-structures)
3. [Semantic Domains](#3-semantic-domains)
   - 3.1 [Voltage Domain](#31-voltage-domain)
   - 3.2 [Pin Domain](#32-pin-domain)
   - 3.3 [Component Domain](#33-component-domain)
    - 3.4 [Power Budget Domain](#34-power-budget-domain)
    - 3.4.1 [Constraint Expression Domain](#341-constraint-expression-domain)
     - 3.4.2 [Sampling Domain](#342-sampling-domain)
     - 3.4.3 [Multi-Broker Domain](#343-multi-broker-domain)
     - 3.4.4 [Alert Trigger Domain](#344-alert-trigger-domain)
     - 3.5 [Connection Domain](#35-connection-domain)
     - 3.5.1 [SmartConnect Domain](#351-smartconnect-domain)
   - 3.6 [Protocol Domain](#36-protocol-domain)
   - 3.7 [Device Model Domain](#37-device-model-domain)
4. [Abstract Syntax](#4-abstract-syntax)
   - 4.1 [Syntax Categories](#41-syntax-categories)
   - 4.2 [Syntactic Well-Formedness](#42-syntactic-well-formedness)
5. [Static Semantics](#5-static-semantics)
   - 5.1 [Type System](#51-type-system)
   - 5.2 [Scope and Binding](#52-scope-and-binding)
6. [Semantic Rules](#6-semantic-rules)
   - 6.1 [Power Connection Semantics](#61-power-connection-semantics)
   - 6.2 [Data Connection Semantics](#62-data-connection-semantics)
   - 6.3 [Protocol Semantics](#63-protocol-semantics)
     - 6.3.1 [GPIO Protocol](#631-gpio-protocol)
     - 6.3.2 [PWM Protocol](#632-pwm-protocol)
   - 6.4 [SmartConnect Resolution Semantics](#64-smartconnect-resolution-semantics)
7. [Well-Formedness Constraints](#7-well-formedness-constraints)
   - 7.1 [Structural Well-Formedness](#71-structural-well-formedness)
   - 7.2 [Referential Integrity](#72-referential-integrity)
8. [Safety Properties](#8-safety-properties)
    - 8.1 [Electrical Safety](#81-electrical-safety)
    - 8.2 [Protocol Safety](#82-protocol-safety)
    - 8.3 [Resource Safety](#83-resource-safety)
    - 8.4 [SmartConnect Safety](#84-smartconnect-safety)
    - 8.5 [Power Budget Safety](#85-power-budget-safety)
    - 8.6 [Pin Function Safety](#86-pin-function-safety)
    - 8.7 [User-Defined Constraint Safety](#87-user-defined-constraint-safety)
     - 8.8 [Sampling Safety](#88-sampling-safety)
     - 8.9 [Multi-Broker Safety](#89-multi-broker-safety)
9. [Validation Algorithm](#9-validation-algorithm)
10. [Formal Proofs](#10-formal-proofs)
11. [Error Recovery and Reporting](#11-error-recovery-and-reporting)
    - 11.1 [Syntax Error Translation](#111-syntax-error-translation)
    - 11.2 [Parser Robustness Properties](#112-parser-robustness-properties)
    - 11.3 [Performance Bounds](#113-performance-bounds)

---

## 1. Introduction

This document provides a formal mathematical specification of the DeMoL (Device Modeling Language) semantics. The formalization follows principles from denotational semantics and type theory to provide a rigorous foundation for:

1. **Static verification** of device models
2. **Correctness guarantees** for hardware configurations
3. **Safety properties** preventing physical damage
4. **Code generation** with proven correctness

### 1.1 Design Philosophy

DeMoL semantics are designed around three core principles:

- **Soundness**: If a model validates, it represents a physically realizable and safe device
- **Completeness**: All physically valid configurations can be expressed
- **Decidability**: All semantic checks terminate in finite time

---

## 2. Mathematical Foundations

### 2.1 Notation and Conventions

#### Set Theory
- $\mathbb{N}$ : Natural numbers $\{0, 1, 2, \ldots\}$
- $\mathbb{R}$ : Real numbers
- $\mathbb{R}^+$ : Positive real numbers
- $\mathbb{B}$ : Boolean values $\{\mathsf{true}, \mathsf{false}\}$
- $\mathcal{P}(S)$ : Power set of $S$
- $S \to T$ : Total functions from $S$ to $T$
- $S \rightharpoonup T$ : Partial functions from $S$ to $T$

#### Relations
- $\subseteq$ : Subset relation
- $\in$ : Element membership
- $\cap$ : Set intersection
- $\cup$ : Set union  
- $\emptyset$ : Empty set
- $|S|$ : Cardinality of set $S$

#### Logic
- $\forall$ : Universal quantification
- $\exists$ : Existential quantification
- $\land$ : Logical AND
- $\lor$ : Logical OR
- $\neg$ : Logical NOT
- $\Rightarrow$ : Logical implication
- $\Leftrightarrow$ : Logical equivalence

### 2.2 Basic Structures

#### Strings and Identifiers
$$\begin{align*}
\mathit{String} &= \text{finite sequences over Unicode} \\
\mathit{Identifier} &= \{\alpha \in \mathit{String} \mid \alpha \text{ matches } [a-zA-Z\_][a-zA-Z0-9\_]*\}
\end{align*}$$

#### Attributes
An attribute is a key-value pair with type information:
$$\mathit{Attribute} = \mathit{Identifier} \times \mathit{Type} \times \mathit{Value}$$

---

## 3. Semantic Domains

### 3.1 Voltage Domain

#### Definition
The voltage domain represents electrical potential differences:
$$\mathit{Voltage} = \mathbb{R} \cup \{\mathsf{GND}\}$$

where $\mathsf{GND}$ represents the ground reference (0V).

#### Voltage Parsing Function
$$\lbrack\!\lbrack \cdot \rbrack\!\rbrack_{V} : \mathit{String} \rightharpoonup \mathit{Voltage}$$

Defined by:
$$\lbrack\!\lbrack s \rbrack\!\rbrack_{V} = \begin{cases}
\mathsf{GND} & \text{if } s \in \{\text{"GND"}, \text{"gnd"}, \text{"0V"}\} \\
v & \text{if } s = v\text{"V"} \land v \in \mathbb{R}^+ \\
v & \text{if } s = v\text{"V3"} \land v = 3.3 \\
v & \text{if } s = v\text{"V5"} \land v = 5.0 \\
\bot & \text{otherwise (undefined)}
\end{cases}$$

#### Compatibility Relation
Two voltages are compatible if their difference is within tolerance:
$$\mathit{compat} : \mathit{Voltage} \times \mathit{Voltage} \to \mathbb{B}$$

$$\mathit{compat}(v_1, v_2) \Leftrightarrow \begin{cases}
\mathsf{true} & \text{if } v_1 = v_2 = \mathsf{GND} \\
\mathsf{true} & \text{if } v_1, v_2 \in \mathbb{R}^+ \land |v_1 - v_2| \leq \tau \\
\mathsf{false} & \text{otherwise}
\end{cases}$$

where $\tau = 0.5$ (tolerance in volts).

### 3.2 Pin Domain

#### Pin Functions
$$\mathit{PinFunction} = \{\mathsf{GPIO}, \mathsf{PWM}, \mathsf{ADC}, \mathsf{DAC}\} \cup \mathit{BusFunction}$$

where:
$$\mathit{BusFunction} = \mathit{I2CFunction} \cup \mathit{SPIFunction} \cup \mathit{UARTFunction}$$

$$\begin{align*}
\mathit{I2CFunction} &= \{\mathsf{SDA}, \mathsf{SCL}\} \times \mathbb{N} \\
\mathit{SPIFunction} &= \{\mathsf{MOSI}, \mathsf{MISO}, \mathsf{SCK}, \mathsf{CS}\} \times \mathbb{N} \\
\mathit{UARTFunction} &= \{\mathsf{TX}, \mathsf{RX}\} \times \mathbb{N}
\end{align*}$$

The second component is the bus index.

#### Pin Structure
A pin is defined as a tuple:
$$\mathit{Pin} = \mathit{Identifier} \times \mathbb{N} \times \mathit{Voltage} \times \mathcal{P}(\mathit{PinFunction}) \times \mathbb{B}$$

Components: $(name, number, voltage, functions, essential)$

#### Pin Projection Functions
$$\begin{align*}
\pi_{name} &: \mathit{Pin} \to \mathit{Identifier} \\
\pi_{num} &: \mathit{Pin} \to \mathbb{N} \\
\pi_{volt} &: \mathit{Pin} \to \mathit{Voltage} \\
\pi_{func} &: \mathit{Pin} \to \mathcal{P}(\mathit{PinFunction}) \\
\pi_{ess} &: \mathit{Pin} \to \mathbb{B}
\end{align*}$$

### 3.3 Component Domain

#### Component Types
$$\mathit{CompType} = \{\mathsf{Board}, \mathsf{Peripheral}, \mathsf{PowerSource}\}$$

#### Component Structure
$$\begin{align*}
\mathit{Component} = &\; \mathit{Identifier} \times \mathit{CompType} \times \mathcal{P}(\mathit{Pin}) \\
&\times \mathit{Voltage} \times \mathit{Voltage} \times \mathit{Attributes}
\end{align*}$$

Components: $(name, type, pins, v_{cc}, v_{io}, attrs)$

where:
- $v_{cc}$ is the component's operating voltage
- $v_{io}$ is the I/O logic level voltage
- $attrs$ are component-specific attributes

### 3.4 Power Budget Domain

#### Power Consumption
$$\mathit{PowerConsumption} = \mathbb{R}^+ \times \mathit{PowerUnit}$$

where $\mathit{PowerUnit} = \{\mathsf{W}, \mathsf{mW}, \mathsf{uW}\}$.

#### Normalization to milliwatts
$$\mathit{toMW} : \mathit{PowerConsumption} \to \mathbb{R}^+$$

$$\mathit{toMW}(v, u) = \begin{cases}
v \times 1000 & \text{if } u = \mathsf{W} \\
v & \text{if } u = \mathsf{mW} \\
v / 1000 & \text{if } u = \mathsf{uW}
\end{cases}$$

#### Component Power Profile
Each component declares a power profile:
$$\mathit{PowerProfile} = \mathit{PowerConsumption}^? \times \mathit{PowerConsumption}^? \times \mathit{PowerConsumption}^?$$

Components: $(P_{min}, P_{max}, P_{avg})$

#### Battery Capacity
$$\mathit{Capacity} = \mathbb{R}^+ \times \mathit{CapacityUnit}$$

where $\mathit{CapacityUnit} = \{\mathsf{mAh}, \mathsf{Ah}, \mathsf{Wh}\}$.

#### Peripheral Supply Budget
The board's available power for peripherals:
$$\mathit{budget}(board) = V_{cc}(board) \times I_{max}(V_{cc}) - P_{avg}(board)$$

where $I_{max}$ is the maximum current for the voltage rail (a platform-specific constant).

#### Protocol Priority for Pin Functions
$$\mathsf{priority} : \mathit{PinFunction} \to \mathbb{N}$$

$$\mathsf{priority}(f) = \begin{cases}
4 & \text{if } f \in \mathit{I2CFunction} \\
3 & \text{if } f \in \mathit{SPIFunction} \\
2 & \text{if } f \in \mathit{UARTFunction} \\
1 & \text{if } f = \mathsf{PWM} \\
0 & \text{if } f \in \{\mathsf{GPIO}, \mathsf{ADC}, \mathsf{DAC}\}
\end{cases}$$

#### 3.4.1 Constraint Expression Domain

User-defined constraints allow model authors to express domain-specific invariants that are checked during semantic validation.

#### Constraint Structure
$$\mathit{UserConstraint} = \mathit{Identifier} \times \mathit{ConstraintExpr} \times \mathit{String}^?$$

Components: $(name, expr, message)$

#### Constraint Expression Grammar
$$\mathit{ConstraintExpr} = \mathit{AdditiveExpr} \times \mathit{CompOp} \times \mathit{AdditiveExpr}$$

$$\mathit{CompOp} = \{<, >, \leq, \geq, =, \neq\}$$

$$\mathit{AdditiveExpr} = \mathit{MultExpr} \times (\mathit{AddOp} \times \mathit{MultExpr})^*$$

$$\mathit{MultExpr} = \mathit{AtomExpr} \times (\mathit{MulOp} \times \mathit{AtomExpr})^*$$

$$\mathit{AtomExpr} = \mathit{FuncCall} \mid \mathit{PropAccess} \mid \mathit{NumLit} \mid \mathit{StrLit} \mid \mathit{BoolLit}$$

#### Built-in Functions
$$\mathit{BuiltinFunc} = \{\mathsf{count}, \mathsf{sum\_power}, \mathsf{avg\_power}, \mathsf{max\_power}\}$$

$$\mathit{FuncArg} = \{\mathsf{SENSOR}, \mathsf{ACTUATOR}, \mathsf{PERIPHERAL}, \mathsf{CONNECTION}\}$$

#### Evaluation Semantics
$$\mathcal{E} : \mathit{AtomExpr} \times \mathit{Device} \to \mathit{Value}$$

$$\mathcal{E}(\mathsf{count}(k), D) = |\{p \in \mathit{peripherals}(D) : \mathit{kind}(p) \in k\}|$$

$$\mathcal{E}(\mathsf{sum\_power}(k), D) = \sum_{p \in \mathit{peripherals}_k(D)} \mathit{toMW}(P_{max}(p))$$

$$\mathcal{E}(c.a, D) = \begin{cases}
\mathit{userAttr}(c, a) & \text{if defined in WITH clause} \\
\mathit{opAttr}(c, a) & \text{if defined in operational block} \\
\bot & \text{otherwise (evaluation error)}
\end{cases}$$

#### Unit Normalization
Numeric literals with units are normalized to base units before comparison:
$$\mathit{normalize}(v, u) = v \times \mathit{factor}(u)$$

where $\mathit{factor}$ maps power units to mW, capacity units to mAh, current units to mA, and frequency units to Hz.

#### 3.4.2 Sampling Domain

A sampling configuration defines the data acquisition parameters for a peripheral:
$$\mathit{SamplingConfig} = \mathit{ComponentRef} \times \mathbb{R}^+ \times \mathit{FreqUnit} \times \mathit{SamplingMode}^? \times \mathbb{N}^? \times \mathbb{R}^?$$

Components: $(target, rate, rate\_unit, mode, buffer, threshold)$

$$\mathit{SamplingMode} = \{\mathsf{continuous}, \mathsf{on\_change}, \mathsf{on\_demand}, \mathsf{batch}\}$$

#### Frequency Normalization

$$\mathit{toHz} : \mathbb{R}^+ \times \mathit{FreqUnit} \to \mathbb{R}^+$$

$$\mathit{toHz}(r, u) = r \times \begin{cases}
10^9 & \text{if } u = \mathsf{ghz} \\
10^6 & \text{if } u = \mathsf{mhz} \\
10^3 & \text{if } u = \mathsf{khz} \\
1 & \text{if } u = \mathsf{hz}
\end{cases}$$

#### Typing Judgments

**Sampling Target Typing** — a SAMPLING block is well-typed only if its target is a peripheral (sensor or actuator), not a board:

$$\frac{
\Gamma \vdash s.\mathit{target} : \tau \quad \tau \in \{\mathsf{Sensor}, \mathsf{Actuator}\}
}{
\Gamma \vdash \mathsf{SAMPLING}\; s : \mathsf{Valid}
} \; [\text{T-Sampling}]$$

**Sampling Mode Typing** — each mode imposes requirements on optional fields:

$$\frac{
s.\mathit{mode} = \mathsf{on\_change} \quad s.\mathit{threshold} > 0
}{
\Gamma \vdash s : \mathsf{Well\text{-}typed}
} \; [\text{T-Sampling-OnChange}]$$

$$\frac{
s.\mathit{mode} = \mathsf{batch} \quad s.\mathit{buffer} > 0
}{
\Gamma \vdash s : \mathsf{Well\text{-}typed}
} \; [\text{T-Sampling-Batch}]$$

$$\frac{
s.\mathit{mode} \in \{\mathsf{continuous}, \mathsf{on\_demand}\}
}{
\Gamma \vdash s : \mathsf{Well\text{-}typed}
} \; [\text{T-Sampling-Simple}]$$

#### Operational Semantics (State Machine)

Each sampling mode defines a distinct runtime behavior. We formalize this as a labeled transition system:

$$\langle \mathit{State}, \mathit{Event}, \to \rangle$$

**State space:**
$$\mathit{SamplingState} = \{\mathsf{Idle}, \mathsf{Reading}, \mathsf{Publishing}, \mathsf{Buffering}, \mathsf{Waiting}\}$$

**Continuous mode** — sample and publish every tick:

$$\frac{
\mathit{tick}(rate)
}{
\mathsf{Idle} \xrightarrow{\mathit{tick}} \mathsf{Reading} \xrightarrow{\mathit{read}} \mathsf{Publishing} \xrightarrow{\mathit{send}} \mathsf{Idle}
} \; [\text{Op-Continuous}]$$

**On-change mode** — sample every tick, publish only when data changes beyond threshold:

$$\frac{
\mathit{tick}(rate) \quad |\mathit{current} - \mathit{previous}| > threshold
}{
\mathsf{Idle} \xrightarrow{\mathit{tick}} \mathsf{Reading} \xrightarrow{\Delta > \tau} \mathsf{Publishing} \xrightarrow{\mathit{send}} \mathsf{Idle}
} \; [\text{Op-OnChange-Publish}]$$

$$\frac{
\mathit{tick}(rate) \quad |\mathit{current} - \mathit{previous}| \leq threshold
}{
\mathsf{Idle} \xrightarrow{\mathit{tick}} \mathsf{Reading} \xrightarrow{\Delta \leq \tau} \mathsf{Idle}
} \; [\text{Op-OnChange-Skip}]$$

**Batch mode** — accumulate $n$ samples, then publish all at once:

$$\frac{
\mathit{tick}(rate) \quad |\mathit{batch}| < buffer
}{
\mathsf{Idle} \xrightarrow{\mathit{tick}} \mathsf{Reading} \xrightarrow{\mathit{read}} \mathsf{Buffering}[\mathit{batch} \cup \{\mathit{sample}\}] \xrightarrow{} \mathsf{Idle}
} \; [\text{Op-Batch-Accumulate}]$$

$$\frac{
|\mathit{batch}| \geq buffer
}{
\mathsf{Buffering} \xrightarrow{\mathit{flush}} \mathsf{Publishing} \xrightarrow{\mathit{send\_all}} \mathsf{Idle}[\mathit{batch} := \emptyset]
} \; [\text{Op-Batch-Flush}]$$

**On-demand mode** — read only when externally triggered:

$$\frac{
\mathit{request}
}{
\mathsf{Waiting} \xrightarrow{\mathit{request}} \mathsf{Reading} \xrightarrow{\mathit{read}} \mathsf{Publishing} \xrightarrow{\mathit{send}} \mathsf{Waiting}
} \; [\text{Op-OnDemand}]$$

#### Denotational Semantics

The denotation of a sampling configuration is a function from sensor state streams to message streams:

$$\lbrack\!\lbrack \cdot \rbrack\!\rbrack_{S} : \mathit{SamplingConfig} \to (\mathit{SensorState}^\omega \to \mathit{Message}^\omega)$$

$$\lbrack\!\lbrack s \rbrack\!\rbrack_{S} = \begin{cases}
\lambda \sigma. \mathit{every}(\mathit{rate}, \sigma) & \text{if } s.\mathit{mode} = \mathsf{continuous} \\
\lambda \sigma. \mathit{filter}(\Delta > \tau, \mathit{every}(\mathit{rate}, \sigma)) & \text{if } s.\mathit{mode} = \mathsf{on\_change} \\
\lambda \sigma. \mathit{batch}(n, \mathit{every}(\mathit{rate}, \sigma)) & \text{if } s.\mathit{mode} = \mathsf{batch} \\
\lambda \sigma. \mathit{onRequest}(\sigma) & \text{if } s.\mathit{mode} = \mathsf{on\_demand}
\end{cases}$$

where:
- $\mathit{every}(r, \sigma)$ samples stream $\sigma$ at rate $r$ Hz
- $\mathit{filter}(p, \sigma)$ passes only elements satisfying predicate $p$
- $\mathit{batch}(n, \sigma)$ groups $n$ consecutive elements
- $\mathit{onRequest}(\sigma)$ returns the latest element on external trigger

#### Code Generation Semantics

The code generator maps sampling configurations to platform-specific runtime artifacts:

$$\mathcal{G}_S : \mathit{SamplingConfig} \times \mathit{Platform} \to \mathit{Code}$$

**RPi Python generation:**

$$\mathcal{G}_S(s, \mathsf{RPi}) = \begin{cases}
\texttt{Rate}(\mathit{rate\_hz}) + \texttt{loop\{read; send; sleep\}} & \text{if continuous} \\
\texttt{Rate}(\mathit{rate\_hz}) + \texttt{loop\{read; if\_changed(}\tau\texttt{); send; sleep\}} & \text{if on\_change} \\
\texttt{Rate}(\mathit{rate\_hz}) + \texttt{loop\{read; append; if\_full(}n\texttt{); flush; sleep\}} & \text{if batch} \\
\texttt{Rate}(\mathit{rate\_hz}) + \texttt{loop\{read; sleep\}} & \text{if on\_demand}
\end{cases}$$

**RiotOS C generation:**

$$\mathcal{G}_S(s, \mathsf{RiotOS}) = \begin{cases}
\texttt{\#define SAMPLING\_INTERVAL\_MS } \lfloor 1000/\mathit{rate\_hz} \rfloor & \\
\texttt{\#define SAMPLING\_MODE } m & \\
\texttt{\#define BATCH\_SIZE } n & \text{(if batch)} \\
\texttt{\#define CHANGE\_THRESHOLD } \tau & \text{(if on\_change)}
\end{cases}$$

The generated code structure preserves the operational semantics defined above: each mode maps to a distinct control flow pattern in the generated `run()` / `read_loop()` function.

#### 3.4.3 Multi-Broker Domain

A device model may declare multiple message brokers:

$$\mathit{Brokers} = \mathit{MessageBroker}^*$$

Each broker has a unique name within the model:

$$\forall b_1, b_2 \in \mathit{Brokers} : b_1.\mathit{name} = b_2.\mathit{name} \Rightarrow b_1 = b_2$$

#### VIA Routing

Connections may specify a target broker via the `VIA` clause:

$$\mathit{via} : \mathit{Connection} \rightharpoonup \mathit{BrokerName}$$

The resolved broker for a connection is:

$$\mathit{resolvedBroker}(c) = \begin{cases} \mathit{brokerMap}(c.\mathit{via}) & \text{if } c.\mathit{via} \neq \bot \\ \mathit{brokers}[0] & \text{otherwise (default)} \end{cases}$$

Topic format validation is performed against the resolved broker's type (MQTT, AMQP, Redis).

#### 3.4.4 Alert Trigger Domain

An alert trigger defines a threshold-based condition on a sensor that fires actions:

$$\mathit{AlertTrigger} = \mathit{Name} \times \mathit{Source} \times \mathit{Condition} \times \mathit{Actions}^+ \times \mathit{Cooldown}?$$

where:
- $\mathit{Source} \in \mathit{Sensors}(D)$ — must be a sensor, not an actuator or board
- $\mathit{Condition} = \mathit{AlertConditionExpr}$ — recursive boolean expression tree
- $\mathit{Actions} = \mathit{AlertPublish} \mid \mathit{AlertActivate}$

#### Alert Condition

$$\mathit{AlertConditionExpr} = \mathit{AlertComparison} \times (\mathit{LogicOp} \times \mathit{AlertConditionExpr})?$$

$$\mathit{AlertComparison} = \mathit{Property} \times \mathit{CompOp} \times \mathit{Value} \times \mathit{Unit}?$$

$$\mathit{LogicOp} = \texttt{\&\&} \mid \texttt{||}$$

#### Alert Actions

$$\mathit{AlertPublish} = \mathit{Topic} \times \mathit{VIA}?$$
$$\mathit{AlertActivate} = \mathit{Target} \quad \text{where } \mathit{Target} \in \mathit{Actuators}(D)$$

#### Typing Judgments

**Alert Source Typing** — the source must be a sensor:

$$\frac{
\Gamma \vdash a.\mathit{source} : \mathsf{Sensor}
}{
\Gamma \vdash \mathsf{ALERT}\; a : \mathsf{Source\text{-}Valid}
} \; [\text{T-Alert-Source}]$$

**Alert ACTIVATE Target Typing** — targets must be actuators and distinct from source:

$$\frac{
\Gamma \vdash act.\mathit{target} : \mathsf{Actuator} \quad act.\mathit{target} \neq a.\mathit{source}
}{
\Gamma \vdash \mathsf{ACTIVATE}\; act \text{ in } a : \mathsf{Valid}
} \; [\text{T-Alert-Activate}]$$

**Alert VIA Typing** — VIA references must resolve to declared brokers:

$$\frac{
pub.\mathit{via} = \bot \lor pub.\mathit{via} \in \mathit{brokerNames}(D)
}{
\Gamma \vdash \mathsf{PUBLISH}\; pub \text{ in } a : \mathsf{Valid}
} \; [\text{T-Alert-Publish}]$$

**Alert Typing (composite):**

$$\frac{
\Gamma \vdash a : \mathsf{Source\text{-}Valid} \quad
\forall act \in a.\mathit{actions} : \Gamma \vdash act \text{ in } a : \mathsf{Valid} \quad
\mathcal{E}_A(a.\mathit{condition}) \neq \bot
}{
\Gamma \vdash \mathsf{ALERT}\; a : \mathsf{Well\text{-}typed}
} \; [\text{T-Alert}]$$

#### Condition Evaluation Semantics

The alert condition is a recursive boolean expression tree. We define evaluation as:

$$\mathcal{E}_A : \mathit{AlertConditionExpr} \times \mathit{SensorReading} \to \mathbb{B}$$

**Comparison evaluation:**
$$\mathcal{E}_A(\mathit{prop} \; \mathit{op} \; v, \; r) = \mathit{op}(\pi_{prop}(r), \; \mathit{normalize}(v, u))$$

where $\pi_{prop}(r)$ extracts the named property from sensor reading $r$ and $\mathit{normalize}$ converts units.

**Logical composition (right-recursive):**
$$\mathcal{E}_A(l \;\texttt{\&\&}\; r, \; s) = \mathcal{E}_A(l, s) \land \mathcal{E}_A(r, s)$$

$$\mathcal{E}_A(l \;\texttt{||}\; r, \; s) = \mathcal{E}_A(l, s) \lor \mathcal{E}_A(r, s)$$

**Precedence:** `&&` and `||` are right-associative with equal precedence (no short-circuit optimization in the DSL; both branches are always evaluated at the model level).

#### Operational Semantics (Reactive Model)

An alert trigger operates as a reactive monitor over the sensor's data stream. We formalize this as a Mealy machine:

$$\langle \mathit{AlertState}, \mathit{SensorReading}, \mathit{ActionSet}, \delta, \omega \rangle$$

**State space:**
$$\mathit{AlertState} = \{\mathsf{Armed}, \mathsf{Firing}, \mathsf{Cooldown}(t_{remaining})\}$$

**Transition function:**

$$\delta(\mathsf{Armed}, r) = \begin{cases}
\mathsf{Firing} & \text{if } \mathcal{E}_A(\mathit{condition}, r) = \mathsf{true} \\
\mathsf{Armed} & \text{otherwise}
\end{cases}$$

$$\delta(\mathsf{Firing}, r) = \begin{cases}
\mathsf{Cooldown}(T_{cd}) & \text{if } \mathit{cooldown} \neq \bot \\
\mathsf{Armed} & \text{otherwise}
\end{cases}$$

$$\delta(\mathsf{Cooldown}(t), r) = \begin{cases}
\mathsf{Armed} & \text{if } t \leq 0 \\
\mathsf{Cooldown}(t - \Delta t) & \text{otherwise}
\end{cases}$$

where $T_{cd} = 1 / \mathit{toHz}(\mathit{cooldown}, \mathit{cooldown\_unit})$ seconds.

**Output function** — actions are emitted only on the $\mathsf{Armed} \to \mathsf{Firing}$ transition:

$$\omega(\mathsf{Armed} \to \mathsf{Firing}) = \mathit{actions}(a)$$
$$\omega(\mathit{otherwise}) = \emptyset$$

**Action execution** is non-blocking and ordered:

$$\mathit{exec}(\mathit{actions}) = \mathit{seq}(\mathit{map}(\lambda act. \begin{cases}
\mathit{publish}(act.\mathit{topic}, \mathit{resolvedBroker}(act)) & \text{if } act : \mathit{AlertPublish} \\
\mathit{activate}(act.\mathit{target}) & \text{if } act : \mathit{AlertActivate}
\end{cases}, \mathit{actions}))$$

#### Denotational Semantics

The denotation of an alert is a function from sensor reading streams to action event streams:

$$\lbrack\!\lbrack \cdot \rbrack\!\rbrack_{A} : \mathit{AlertTrigger} \to (\mathit{SensorReading}^\omega \to \mathit{ActionEvent}^\omega)$$

$$\lbrack\!\lbrack a \rbrack\!\rbrack_{A} = \lambda \sigma. \mathit{throttle}(T_{cd}, \mathit{filter}(\lambda r. \mathcal{E}_A(a.\mathit{condition}, r), \sigma) \gg\!\!= \lambda r. a.\mathit{actions})$$

where:
- $\mathit{filter}$ selects readings where the condition is true
- $\gg\!\!=$ (bind) maps each matching reading to the action set
- $\mathit{throttle}(T_{cd}, \cdot)$ suppresses events within $T_{cd}$ seconds of the previous firing

Without cooldown ($T_{cd} = 0$), the alert fires on every reading that satisfies the condition.

#### Code Generation Semantics

$$\mathcal{G}_A : \mathit{AlertTrigger} \times \mathit{Platform} \to \mathit{Code}$$

Alert code generation produces a condition-check block embedded in the sampling loop:

$$\mathcal{G}_A(a, \mathsf{RPi}) = \texttt{if } \mathcal{G}_{cond}(a.\mathit{condition}) \texttt{ and not cooling\_down:} \; \mathit{action\_code}$$

where:
$$\mathcal{G}_{cond}(l \;\texttt{\&\&}\; r) = \mathcal{G}_{cond}(l) \texttt{ and } \mathcal{G}_{cond}(r)$$
$$\mathcal{G}_{cond}(l \;\texttt{||}\; r) = \mathcal{G}_{cond}(l) \texttt{ or } \mathcal{G}_{cond}(r)$$
$$\mathcal{G}_{cond}(\mathit{prop} \; \mathit{op} \; v) = \texttt{data["}\mathit{prop}\texttt{"] } \mathit{op} \texttt{ } v$$

#### Interaction: SAMPLING × ALERT

When both SAMPLING and ALERT are declared for the same sensor, the alert condition is evaluated at the sampling rate:

$$\mathit{alertRate}(a) = \begin{cases}
\mathit{toHz}(s.\mathit{rate}, s.\mathit{unit}) & \text{if } \exists s \in \mathit{samplings} : s.\mathit{target} = a.\mathit{source} \\
f_{default} & \text{otherwise}
\end{cases}$$

The alert evaluation frequency is bounded by: $\mathit{alertRate}(a) \leq \mathit{toHz}(s.\mathit{rate}, s.\mathit{unit})$. The alert cannot fire faster than the sensor is sampled.

**Effective cooldown constraint:**
$$T_{cd} \geq 1 / \mathit{alertRate}(a) \quad \text{(trivially satisfied; cooldown is always } \geq 1 \text{ tick)}$$

#### Alert Syntax

```
ALERT <name> ON <sensor> WHEN
    <property> <op> <value> [&& | || <property> <op> <value>]*
    THEN
    (PUBLISH <topic> [VIA <broker>])*
    (ACTIVATE <actuator>)*
    [COOLDOWN <number> <freq-unit>]
;
```

### 3.5 Connection Domain

#### Power Connection
$$\mathit{PowerConn} = \mathit{Pin} \times \mathit{Pin}$$

Represents a power connection from source pin to sink pin.

#### Data Connection
$$\mathit{DataConn} = \mathit{Protocol} \times \mathcal{P}(\mathit{PinMapping}) \times \mathit{Properties}$$

where:
$$\mathit{PinMapping} = \mathit{Identifier} \times \mathit{Pin} \times \mathit{Pin}$$

Components: $(function, source\_pin, sink\_pin)$

$$\mathit{Properties} = \mathit{Identifier} \rightharpoonup \mathit{Value}$$

#### Connection Structure
A connection links two components:
$$\mathit{Connection} = \mathit{Component} \times \mathit{Component} \times \mathcal{P}(\mathit{PowerConn}) \times \mathcal{P}(\mathit{DataConn})$$

Components: $(comp_1, comp_2, power\_conns, data\_conns)$

#### 3.5.1 SmartConnect Domain

A SmartConnect declaration requests automatic pin resolution:
$$\mathit{SmartConnDecl} = \mathit{ComponentRef} \times \mathit{Topic}?$$

where $\mathit{ComponentRef}$ references a peripheral instance and $\mathit{Topic} \in \mathit{String}$ is an optional broker topic.

#### Pin Pool

The pin pool tracks board pin availability during resolution:
$$\mathit{PinPool} = \mathit{Identifier} \rightharpoonup (\mathit{Identifier} \times \mathit{UsageType})^*$$

where:
$$\mathit{UsageType} = \{\mathsf{POWER}, \mathsf{I2C\text{-}SDA}, \mathsf{I2C\text{-}SCL}, \mathsf{SPI}, \mathsf{UART}, \mathsf{PWM}, \mathsf{GPIO}\}$$

#### Shareability Predicate

$$\mathsf{shareable}(u) \Leftrightarrow u \in \{\mathsf{POWER}, \mathsf{I2C\text{-}SDA}, \mathsf{I2C\text{-}SCL}\}$$

#### Pin Availability

$$\mathsf{available}(pin, u, \mathit{pool}) \Leftrightarrow pin \notin \mathsf{dom}(\mathit{pool}) \lor (\mathsf{shareable}(u) \land \forall (id, u') \in \mathit{pool}(pin) : u' = u)$$

### 3.6 Protocol Domain

#### Protocol Types
$$\mathit{Protocol} = \{\mathsf{GPIO}, \mathsf{I2C}, \mathsf{SPI}, \mathsf{UART}, \mathsf{PWM}\}$$

#### Protocol Properties
Each protocol has required properties:
$$\mathit{ProtocolProps} : \mathit{Protocol} \to \mathcal{P}(\mathit{Identifier})$$

$$\mathit{ProtocolProps}(\pi) = \begin{cases}
\{\text{mode}, \text{pullup}, \text{pulldown}\} & \text{if } \pi = \mathsf{GPIO} \\
\{\text{slave\_address}, \text{bus\_speed}\} & \text{if } \pi = \mathsf{I2C} \\
\{\text{bus\_speed}, \text{mode}\} & \text{if } \pi = \mathsf{SPI} \\
\{\text{baudrate}, \text{parity}, \text{stop\_bits}, \text{data\_bits}\} & \text{if } \pi = \mathsf{UART} \\
\{\text{frequency}, \text{duty\_cycle}, \text{channel}\} & \text{if } \pi = \mathsf{PWM}
\end{cases}$$

### 3.7 Device Model Domain

#### Device Model Structure
$$\begin{align*}
\mathit{Device} = &\; \mathit{Identifier} \times \mathit{Metadata} \times \mathit{Component} \\
&\times \mathcal{P}(\mathit{Component}) \times \mathcal{P}(\mathit{Component}) \\
&\times \mathcal{P}(\mathit{Connection}) \times \mathcal{P}(\mathit{SmartConnDecl}) \\
&\times \mathit{Broker} \times \mathit{Network}
\end{align*}$$

Components: $(name, metadata, board, peripherals, power\_sources, connections, smart\_conns, broker, network)$

#### Constraints
$$\begin{align*}
|\{board\}| &= 1 \\
\forall p \in peripherals &: \pi_{type}(p) = \mathsf{Peripheral} \\
\forall s \in power\_sources &: \pi_{type}(s) = \mathsf{PowerSource}
\end{align*}$$

---

## 4. Abstract Syntax

### 4.1 Syntax Categories

#### Device Declaration
$$d \in \mathit{DeviceDecl} ::= \mathsf{DEVICE}\; id\; \mathsf{WITH}\; m\; b\; P\; S\; C\; br\; n$$

where:
- $id \in \mathit{Identifier}$ : device name
- $m \in \mathit{Metadata}$ : metadata attributes
- $b \in \mathit{BoardUse}$ : board component
- $P \subseteq \mathit{PeripheralUse}$ : peripheral components
- $S \subseteq \mathit{PowerSourceUse}$ : power sources
- $C \subseteq \mathit{ConnectionDecl}$ : connections
- $br \in \mathit{BrokerDecl}$ : broker configuration
- $n \in \mathit{NetworkDecl}$ : network configuration

#### Component Use
$$u \in \mathit{ComponentUse} ::= \mathsf{USE}\; t[id]\; (\mathsf{WITH}\; a)?$$

where:
- $t \in \mathit{Identifier}$ : component type
- $id \in \mathit{Identifier}$ : instance name
- $a \in \mathit{Attributes}$ : optional attribute overrides

#### Connection Declaration
$$\begin{align*}
c \in \mathit{ConnectionDecl} ::= &\; \mathsf{CONNECT}\; (src\; \mathsf{:})?\; tgt\; \mathsf{WITH} \\
&\; \mathsf{POWER}\; pc^* \\
&\; \mathsf{DATA}\; dc^*
\end{align*}$$

where:
- $src, tgt \in \mathit{Identifier}$ : component names
- $pc \in \mathit{PowerConnSyn}$ : power connection
- $dc \in \mathit{DataConnSyn}$ : data connection

#### Pin Mapping Syntax
$$pm \in \mathit{PinMapSyn} ::= func\; p_1 \; \mathsf{--} \; p_2$$

where:
- $func \in \mathit{Identifier}$ : pin function
- $p_1, p_2 \in \mathit{Identifier}$ : pin names

#### SmartConnect Declaration
$$sc \in \mathit{SmartConnDecl} ::= \mathsf{SMARTCONNECT}\; tgt\; (\mathsf{@}\; topic)?\; \mathsf{;}$$

where:
- $tgt \in \mathit{Identifier}$ : peripheral instance name
- $topic \in \mathit{String}$ : optional broker topic

### 4.2 Syntactic Well-Formedness

A syntactic structure is well-formed if it satisfies:

$$\begin{align*}
\mathsf{WF}_{syn}(d) \Leftrightarrow &\; \mathsf{unique}(\mathit{ids}(P)) \\
\land &\; \mathsf{unique}(\mathit{ids}(S)) \\
\land &\; \forall c \in C : \mathsf{referenced}(c, P \cup S \cup \{b\}) \\
\land &\; \forall sc \in SC : \mathsf{referenced}(sc.tgt, P) \\
\land &\; \mathsf{unique}(\mathit{targets}(SC)) \\
\land &\; \mathit{targets}(SC) \cap \mathit{targets}(C) = \emptyset
\end{align*}$$

where:
- $\mathsf{unique}$ ensures no duplicate identifiers
- $\mathsf{referenced}$ ensures all connection endpoints exist

---

## 5. Static Semantics

### 5.1 Type System

#### Type Environment
$$\Gamma : \mathit{Identifier} \rightharpoonup \mathit{Component}$$

Maps component names to their definitions.

#### Typing Judgments

**Component Typing**
$$\frac{
\Gamma(id) = c \quad c : \tau
}{
\Gamma \vdash id : \tau
}$$

**Connection Typing**
$$\frac{
\Gamma \vdash src : \tau_1 \quad \Gamma \vdash tgt : \tau_2 \quad \mathsf{compatible}(\tau_1, \tau_2, proto)
}{
\Gamma \vdash \mathsf{CONNECT}\; src : tgt\; \mathsf{WITH}\; proto : \mathsf{Valid}
}$$

**SmartConnect Typing**
$$\frac{
\Gamma \vdash tgt : \mathsf{Peripheral} \quad tgt \notin \mathit{targets}(C)
}{
\Gamma \vdash \mathsf{SMARTCONNECT}\; tgt : \mathsf{Valid}
} \; [\text{T-SmartConn}]$$

### 5.2 Scope and Binding

#### Name Resolution
Every identifier must be bound in the scope:
$$\mathsf{resolve} : \mathit{Identifier} \times \Gamma \rightharpoonup \mathit{Component}$$

$$\mathsf{resolve}(id, \Gamma) = \begin{cases}
\Gamma(id) & \text{if } id \in \mathsf{dom}(\Gamma) \\
\bot & \text{otherwise}
\end{cases}$$

#### Scope Rules

**Global Scope**
$$\Gamma_{global} = \{board\} \cup peripherals \cup power\_sources \cup brokers$$

**Connection Scope**
$$\Gamma_{conn} = \Gamma_{global} \cup \{\mathit{pins}(src), \mathit{pins}(tgt)\}$$

---

## 6. Semantic Rules

### 6.1 Power Connection Semantics

#### Rule PC-1: Ground Connections
$$\frac{
\pi_{volt}(p_1) = \mathsf{GND} \quad \pi_{volt}(p_2) = \mathsf{GND}
}{
\mathsf{valid\_power}(p_1, p_2)
} \; [\text{PC-GND}]$$

#### Rule PC-2: Voltage Compatibility
$$\frac{
\pi_{volt}(p_1) = v_1 \in \mathbb{R}^+ \quad \pi_{volt}(p_2) = v_2 \in \mathbb{R}^+ \quad \mathit{compat}(v_1, v_2)
}{
\mathsf{valid\_power}(p_1, p_2)
} \; [\text{PC-VCC}]$$

#### Rule PC-3: No Mixed Connections
$$\frac{
(\pi_{volt}(p_1) = \mathsf{GND} \land \pi_{volt}(p_2) \neq \mathsf{GND}) \lor (\pi_{volt}(p_1) \neq \mathsf{GND} \land \pi_{volt}(p_2) = \mathsf{GND})
}{
\neg \mathsf{valid\_power}(p_1, p_2)
} \; [\text{PC-NO-MIX}]$$

### 6.2 Data Connection Semantics

#### Rule DC-1: Function Matching
For a data connection with protocol $\pi$ and pin mapping $(f, p_1, p_2)$:
$$\frac{
f \in \mathit{RequiredFunctions}(\pi) \quad \exists g_1 \in \pi_{func}(p_1), g_2 \in \pi_{func}(p_2) : \mathsf{matches}(f, g_1, g_2, \pi)
}{
\mathsf{valid\_data}(\pi, f, p_1, p_2)
} \; [\text{DC-FUNC}]$$

#### Function Matching Predicate
$$\mathsf{matches}(f, g_1, g_2, \pi) \Leftrightarrow \begin{cases}
g_1 = \mathsf{GPIO} \land g_2 = \mathsf{GPIO} & \text{if } \pi = \mathsf{GPIO} \\
g_1 = (\mathsf{SDA}, n) \land g_2 = (\mathsf{SDA}, n) \land f = \text{sda} & \text{if } \pi = \mathsf{I2C} \\
g_1 = (\mathsf{SCL}, n) \land g_2 = (\mathsf{SCL}, n) \land f = \text{scl} & \text{if } \pi = \mathsf{I2C} \\
g_1 = (\mathsf{MOSI}, n) \land g_2 = (\mathsf{MOSI}, n) \land f = \text{mosi} & \text{if } \pi = \mathsf{SPI} \\
g_1 = (\mathsf{MISO}, n) \land g_2 = (\mathsf{MISO}, n) \land f = \text{miso} & \text{if } \pi = \mathsf{SPI} \\
g_1 = (\mathsf{SCK}, n) \land g_2 = (\mathsf{SCK}, n) \land f = \text{sck} & \text{if } \pi = \mathsf{SPI} \\
g_1 = (\mathsf{CS}, n) \land g_2 = (\mathsf{CS}, n) \land f = \text{cs} & \text{if } \pi = \mathsf{SPI} \\
g_1 = (\mathsf{TX}, n) \land g_2 = (\mathsf{RX}, n) \land f = \text{tx} & \text{if } \pi = \mathsf{UART} \\
g_1 = (\mathsf{RX}, n) \land g_2 = (\mathsf{TX}, n) \land f = \text{rx} & \text{if } \pi = \mathsf{UART} \\
g_1 = \mathsf{PWM} \land (g_2 = \mathsf{PWM} \lor g_2 = \mathsf{GPIO}) & \text{if } \pi = \mathsf{PWM}
\end{cases}$$

### 6.3 Protocol Semantics

#### I2C Protocol
$$\lbrack\!\lbrack \mathsf{I2C} \rbrack\!\rbrack = \langle \mathit{addr}, \mathit{speed}, \mathit{bus} \rangle$$

**Constraints:**
$$\begin{align*}
\mathit{addr} &\in [0x00, 0x7F] \\
\mathit{speed} &\in \mathbb{N}^+ \\
\mathit{bus} &\in \mathbb{N}
\end{align*}$$

**Semantic Function:**
$$\mathcal{I} : \mathit{DataConn} \rightharpoonup \mathit{I2CSemantics}$$

where $\mathit{I2CSemantics} = \mathit{Address} \times \mathit{Speed} \times \mathit{Bus}$

#### SPI Protocol
$$\lbrack\!\lbrack \mathsf{SPI} \rbrack\!\rbrack = \langle \mathit{mode}, \mathit{speed}, \mathit{bus} \rangle$$

**Constraints:**
$$\begin{align*}
\mathit{mode} &\in \{0, 1, 2, 3\} \\
\mathit{speed} &\in \mathbb{N}^+ \\
\mathit{bus} &\in \mathbb{N}
\end{align*}$$

#### UART Protocol
$$\lbrack\!\lbrack \mathsf{UART} \rbrack\!\rbrack = \langle \mathit{baud}, \mathit{parity}, \mathit{stop}, \mathit{data} \rangle$$

**Constraints:**
$$\begin{align*}
\mathit{baud} &\in \{9600, 19200, 38400, 57600, 115200, \ldots\} \\
\mathit{parity} &\in \{\mathsf{none}, \mathsf{even}, \mathsf{odd}, \mathsf{mark}, \mathsf{space}\} \\
\mathit{stop} &\in \{1, 2\} \\
\mathit{data} &\in \{5, 6, 7, 8\}
\end{align*}$$

#### 6.3.1 GPIO Protocol

$$\lbrack\!\lbrack \mathsf{GPIO} \rbrack\!\rbrack = \langle \mathit{mode}, \mathit{pullup}, \mathit{pulldown} \rangle$$

**Constraints:**
$$\begin{align*}
\mathit{mode} &\in \{\mathsf{input}, \mathsf{output}\} \\
\mathit{pullup} &\in \mathbb{B} \\
\mathit{pulldown} &\in \mathbb{B}
\end{align*}$$

**GPIO Mode Inference** (for SmartConnect):
$$\mathit{inferMode}(p) = \begin{cases}
\mathsf{input} & \text{if } \pi_{type}(p) = \mathsf{Sensor} \\
\mathsf{output} & \text{if } \pi_{type}(p) = \mathsf{Actuator} \\
\mathsf{input} & \text{otherwise (default)}
\end{cases}$$

Per-pin mode overrides may be specified via the `gpio_modes` attribute on the peripheral definition, taking precedence over type-based inference.

#### 6.3.2 PWM Protocol

$$\lbrack\!\lbrack \mathsf{PWM} \rbrack\!\rbrack = \langle \mathit{frequency}, \mathit{duty\_cycle}, \mathit{channel} \rangle$$

**Constraints:**
$$\begin{align*}
\mathit{frequency} &\in \mathbb{R}^+ \\
\mathit{duty\_cycle} &\in [0, 100] \subset \mathbb{R} \\
\mathit{channel} &\in \mathbb{N}
\end{align*}$$

**Semantic Function:**
$$\mathcal{W} : \mathit{DataConn} \rightharpoonup \mathit{PWMSemantics}$$

where $\mathit{PWMSemantics} = \mathit{Frequency} \times \mathit{DutyCycle} \times \mathit{Channel}$

### 6.4 SmartConnect Resolution Semantics

SmartConnect automatically resolves pin assignments by matching peripheral pin requirements against available board pins. Resolution produces synthesized connections that are structurally identical to manual `CONNECT` objects, enabling all existing validators and generators to operate without modification.

#### 6.4.1 Resolution Function

$$\mathcal{R} : \mathit{SmartConnDecl} \times \mathit{Device} \times \mathit{PinPool} \to \mathit{Connection} \times \mathit{PinPool}$$

The resolver takes a SmartConnect declaration, the device model, and the current pin pool state, producing a synthesized connection and an updated pin pool.

#### 6.4.2 Protocol Priority

Pin classification uses a priority ordering to select the primary protocol for multi-function pins:

$$\mathsf{priority} : \mathit{Protocol} \to \mathbb{N}$$

$$\mathsf{priority}(\pi) = \begin{cases}
4 & \text{if } \pi = \mathsf{I2C} \\
3 & \text{if } \pi = \mathsf{SPI} \\
2 & \text{if } \pi = \mathsf{UART} \\
1 & \text{if } \pi = \mathsf{PWM} \\
0 & \text{if } \pi = \mathsf{GPIO}
\end{cases}$$

#### 6.4.3 Pin Classification

Each IO pin is classified by its highest-priority protocol function:

$$\mathsf{classify} : \mathcal{P}(\mathit{Pin}) \to (\mathit{Protocol} \to \mathcal{P}(\mathit{Pin}))$$

$$\mathsf{classify}(\mathit{pins})(\pi) = \{p \in \mathit{pins} \mid \mathsf{primaryProto}(p) = \pi\}$$

where:

$$\mathsf{primaryProto}(p) = \arg\max_{\pi \in \mathit{protos}(p)} \mathsf{priority}(\pi)$$

#### 6.4.4 Sequential Resolution

SmartConnect declarations are resolved sequentially in declaration order, threading the pin pool state:

$$\frac{
\mathit{pool}_{0} = \mathsf{initPool}(board, C) \quad \forall i \in [1, |SC|] : (conn_{i}, \mathit{pool}_{i}) = \mathcal{R}(sc_{i}, D, \mathit{pool}_{i-1})
}{
D' = D[connections := C \cup \{conn_{1}, \ldots, conn_{|SC|}\}]
} \; [\text{SC-SEQ}]$$

#### 6.4.5 Power Pin Resolution

For each power pin on the peripheral, find a compatible board power pin:

$$\frac{
p \in \mathit{powerPins}(periph) \quad bp = \mathsf{findPower}(\mathit{pool}, \pi_{volt}(p)) \quad bp \neq \bot
}{
(p, bp) \in \mathit{power\_conns} \quad \mathit{pool}' = \mathit{pool}[bp \mapsto \mathit{pool}(bp) \cup \{(periph, \mathsf{POWER})\}]
} \; [\text{SC-POWER}]$$

Power pins prefer unused board pins, falling back to already-used shareable pins.

#### 6.4.6 Data Pin Resolution

Data pins are resolved in protocol priority order (I2C first, then SPI, UART, PWM, GPIO):

**I2C Resolution** — requires `i2c_address` attribute on the peripheral:

$$\frac{
p \in \mathsf{classify}(\mathit{ioPins})(\mathsf{I2C}) \quad bp = \mathsf{findFunc}(\mathit{pool}, \pi_{func}(p).type, \pi_{func}(p).bus)
}{
(p, bp) \in \mathit{data\_mappings}
} \; [\text{SC-I2C}]$$

**UART Resolution** — applies TX/RX crossover:

$$\frac{
\pi_{func}(p) = (\mathsf{TX}, n) \quad bp = \mathsf{findFunc}(\mathit{pool}, \mathsf{RX}, n) \quad bp \neq \bot
}{
(p, bp) \in \mathit{data\_mappings}
} \; [\text{SC-UART-CROSS}]$$

$$\frac{
\pi_{func}(p) = (\mathsf{RX}, n) \quad bp = \mathsf{findFunc}(\mathit{pool}, \mathsf{TX}, n) \quad bp \neq \bot
}{
(p, bp) \in \mathit{data\_mappings}
} \; [\text{SC-UART-CROSS}]$$

**GPIO Resolution** — mode inferred from component type:

$$\frac{
p \in \mathsf{classify}(\mathit{ioPins})(\mathsf{GPIO}) \quad bp = \mathsf{findGPIO}(\mathit{pool}) \quad m = \mathit{inferMode}(periph)
}{
(\mathsf{GPIO}, \{(p, bp)\}, \{\text{mode} \mapsto m\}) \in \mathit{data\_conns}
} \; [\text{SC-GPIO}]$$

#### 6.4.7 Determinism

Resolution is deterministic: board pins are sorted by physical pin number, and SmartConnect declarations are processed in declaration order.

$$\forall D, sc, \mathit{pool} : |\{\mathcal{R}(sc, D, \mathit{pool})\}| \leq 1$$

---

## 7. Well-Formedness Constraints

### 7.1 Structural Well-Formedness

#### WF-1: Single Board
$$\mathsf{WF}_{\text{single-board}}(D) \Leftrightarrow |\{board\}| = 1$$

#### WF-2: All Peripherals Connected
$$\mathsf{WF}_{\text{all-connected}}(D) \Leftrightarrow \forall p \in peripherals : (\exists c \in connections : p \in \{c.src, c.tgt\}) \lor (\exists sc \in smart\_conns : sc.tgt = p)$$

#### WF-3: Unique Peripheral Names
$$\mathsf{WF}_{\text{unique-names}}(D) \Leftrightarrow \forall p_1, p_2 \in peripherals : p_1 \neq p_2 \Rightarrow \pi_{name}(p_1) \neq \pi_{name}(p_2)$$

#### WF-4: Unique Pin Numbers
$$\mathsf{WF}_{\text{unique-pins}}(c) \Leftrightarrow \forall p_1, p_2 \in \mathit{pins}(c) : p_1 \neq p_2 \Rightarrow \pi_{num}(p_1) \neq \pi_{num}(p_2)$$

#### WF-5: Essential Pins Connected
$$\mathsf{WF}_{\text{essential}}(D, p) \Leftrightarrow \forall pin \in \mathit{pins}(p) : \pi_{ess}(pin) \Rightarrow \mathsf{connected}(pin, connections)$$

where:
$$\mathsf{connected}(pin, C) \Leftrightarrow \exists c \in C : pin \in \mathsf{usedPins}(c)$$

#### WF-6: SmartConnect Target Type
$$\mathsf{WF}_{\text{sc-target}}(D) \Leftrightarrow \forall sc \in smart\_conns : \pi_{type}(\mathsf{resolve}(sc.tgt, \Gamma)) = \mathsf{Peripheral}$$

SmartConnect can only target sensors and actuators, not boards.

#### WF-7: SmartConnect Uniqueness
$$\mathsf{WF}_{\text{sc-unique}}(D) \Leftrightarrow \forall sc_{1}, sc_{2} \in smart\_conns : sc_{1} \neq sc_{2} \Rightarrow sc_{1}.tgt \neq sc_{2}.tgt$$

Each peripheral can have at most one SmartConnect declaration.

#### WF-8: SmartConnect-Connect Exclusivity
$$\mathsf{WF}_{\text{sc-exclusive}}(D) \Leftrightarrow \mathit{targets}(smart\_conns) \cap \mathit{targets}(connections) = \emptyset$$

A peripheral must use either manual `CONNECT` or `SMARTCONNECT`, not both.

### 7.2 Referential Integrity

#### RI-1: Pin References
$$\mathsf{RI}_{\text{pins}}(c) \Leftrightarrow \forall (f, p_1, p_2) \in c.data\_conns : p_1 \in \mathit{pins}(c.src) \land p_2 \in \mathit{pins}(c.tgt)$$

#### RI-2: Component References
$$\mathsf{RI}_{\text{comp}}(D) \Leftrightarrow \forall c \in connections : \{c.src, c.tgt\} \subseteq \Gamma_{global}$$

#### RI-3: Broker Existence
$$\mathsf{RI}_{\text{broker}}(D) \Leftrightarrow broker \neq \bot$$

#### RI-4: Network Existence
$$\mathsf{RI}_{\text{network}}(D) \Leftrightarrow network \neq \bot$$

---

## 8. Safety Properties

### 8.1 Electrical Safety

#### Safety-1: Pin Conflict Freedom
$$\mathsf{Safety}_{\text{pin-conflicts}}(D) \Leftrightarrow \forall c_1, c_2 \in connections : c_1 \neq c_2 \Rightarrow \mathsf{usedPins}(c_1) \cap \mathsf{usedPins}(c_2) \subseteq \mathsf{shareable}$$

where:
$$\mathsf{shareable} = \{p \mid \pi_{volt}(p) \in \{\mathsf{GND}, \mathit{VCC}\}\} \cup \{p \mid \exists f \in \pi_{func}(p) : f \in \mathit{I2CFunction}\}$$

#### Safety-2: Voltage Limits
$$\mathsf{Safety}_{\text{voltage-limits}}(c, p) \Leftrightarrow \forall pc \in c.power\_conns : c.tgt = p \Rightarrow \pi_{volt}(pc.src) \leq \pi_{volt}(p) + \tau$$

#### Safety-3: IO Voltage Compatibility
$$\mathsf{Safety}_{\text{io-voltage}}(c) \Leftrightarrow \mathit{compat}(\pi_{io}(c.src), \pi_{io}(c.tgt))$$

#### Safety-4: Common Ground
$$\mathsf{Safety}_{\text{common-ground}}(c) \Leftrightarrow \exists pc \in c.power\_conns : \pi_{volt}(pc.src) = \pi_{volt}(pc.tgt) = \mathsf{GND}$$

### 8.2 Protocol Safety

#### Safety-5: I2C Address Uniqueness
$$\mathsf{Safety}_{\text{i2c-unique}}(D) \Leftrightarrow \forall c_1, c_2 \in connections : \mathsf{sameBus}(c_1, c_2) \Rightarrow \mathcal{I}(c_1).addr \neq \mathcal{I}(c_2).addr$$

where:
$$\mathsf{sameBus}(c_1, c_2) \Leftrightarrow \mathsf{busKey}(c_1) = \mathsf{busKey}(c_2)$$

$$\mathsf{busKey}(c) = (\mathit{SDA\_pin}(c), \mathit{SCL\_pin}(c))$$

#### Safety-6: Topic Format
$$\mathsf{Safety}_{\text{topic}}(D, c) \Leftrightarrow \mathsf{validTopic}(c.remote, D.broker.type)$$

where:
$$\mathsf{validTopic}(t, bt) = \begin{cases}
\mathsf{validMQTT}(t) & \text{if } bt = \mathsf{MQTT} \\
\mathsf{validAMQP}(t) & \text{if } bt = \mathsf{AMQP} \\
\mathsf{validRedis}(t) & \text{if } bt = \mathsf{Redis}
\end{cases}$$

### 8.3 Resource Safety

#### Safety-7: Power Path Existence
$$\mathsf{Safety}_{\text{power-path}}(D) \Leftrightarrow \forall p \in peripherals \cup \{board\} : \mathsf{reachable}(p, power\_sources, connections)$$

where reachability is defined transitively:
$$\mathsf{reachable}(p, S, C) \Leftrightarrow p \in S \lor \exists c \in C : c.tgt = p \land \mathsf{reachable}(c.src, S, C)$$

### 8.4 SmartConnect Safety

#### Safety-8: SmartConnect Pin Allocation
$$\mathsf{Safety}_{\text{sc-alloc}}(D) \Leftrightarrow \forall sc \in smart\_conns : \mathcal{R}(sc, D, \mathit{pool}) \neq \bot$$

Every SmartConnect declaration must successfully resolve — all mandatory peripheral pins must find matching available board pins.

#### Safety-9: Resolution Preserves Pin Conflict Freedom
$$\mathsf{Safety}_{\text{sc-conflicts}}(D) \Leftrightarrow \mathsf{Safety}_{\text{pin-conflicts}}(D[connections := connections \cup \mathsf{resolved}(smart\_conns)])$$

After resolution, all connections (manual and synthesized) collectively satisfy pin conflict freedom. This is guaranteed by the shareability predicate in the PinPool.

### 8.5 Power Budget Safety

#### Safety-10: Peripheral Power Budget

The total peak power consumption of all peripherals must not exceed the board's available supply budget:

$$\mathsf{Safety}_{\text{power-budget}}(D) \Leftrightarrow \sum_{p \in peripherals} \mathit{toMW}(P_{max}(p)) \leq \mathit{budget}(board)$$

where:

$$\mathit{budget}(board) = V_{cc}(board) \times I_{max}(V_{cc}) - \mathit{toMW}(P_{avg}(board))$$

This is a **warning** (not an error) because power consumption values are theoretical datasheet maximums. The warning includes a per-peripheral breakdown.

#### Safety-11: Battery Runtime Estimation

When a $\mathit{PowerSource}$ with known capacity is declared, estimate the runtime:

$$\mathit{runtime}(ps) = \frac{\mathit{capacity}(ps)}{\sum_{p \in peripherals} \mathit{toMW}(P_{avg}(p)) \;/\; V_{nominal}(ps)}$$

This is an **informational warning** emitted as `[Info-Battery-Runtime]`.

### 8.6 Pin Function Safety

#### Safety-12: Pin Function Oversubscription

When a multi-function board pin is used at a lower-priority protocol than its highest-priority capability, warn that the higher-priority bus becomes unavailable:

$$\mathsf{Safety}_{\text{pin-oversub}}(D) \Leftrightarrow \forall c \in connections, \forall bp \in \mathit{usedBoardPins}(c) :$$

$$\nexists f_{high} \in \pi_{func}(bp) : \mathsf{priority}(f_{high}) > \mathsf{priority}(\mathsf{usedAs}(bp, c))$$

If the condition is violated, emit a warning identifying the pin, its used-as protocol, and the lost higher-priority functions.

**Example:** If $bp = \text{GPIO2}$ with $\pi_{func} = \{\mathsf{GPIO}, (\mathsf{SDA}, 0)\}$ and $\mathsf{usedAs}(bp, c) = \mathsf{GPIO}$, then $\mathsf{priority}(\mathsf{SDA}) = 4 > 0 = \mathsf{priority}(\mathsf{GPIO})$ triggers a warning that I2C bus 0 SDA is disabled.

### 8.7 User-Defined Constraint Safety

#### Safety-13: Constraint Satisfaction

All user-defined CONSTRAINT expressions must evaluate to true:

$$\mathsf{Safety}_{\text{constraint}}(D) \Leftrightarrow \forall c \in \mathit{constraints}(D) : \mathcal{E}(c.\mathit{expr}, D) = \mathsf{true}$$

If a constraint evaluates to false, a semantic error is raised with the user-provided MESSAGE (or a generated default message showing the evaluated operands).

#### Safety-14: Constraint Evaluability

All constraint expressions must be evaluable against the model:

$$\mathsf{Safety}_{\text{eval}}(D) \Leftrightarrow \forall c \in \mathit{constraints}(D) : \mathcal{E}(c.\mathit{expr}, D) \neq \bot$$

If a constraint references a non-existent peripheral or attribute, a warning is emitted (not an error) since the constraint itself may be conditionally applicable.

**Example:** `CONSTRAINT min_sensors: count(SENSOR) >= 2 MESSAGE "Need redundancy";` raises a semantic error if fewer than 2 sensors are declared.

### 8.8 Sampling Safety

#### Safety-15: Positive Sampling Rate

All SAMPLING configurations must specify a strictly positive rate:

$$\mathsf{Safety}_{\text{rate}}(D) \Leftrightarrow \forall s \in \mathit{samplings}(D) : \mathit{toHz}(s.\mathit{rate}, s.\mathit{rate\_unit}) > 0$$

where $\mathit{toHz}$ normalizes the rate to Hertz using the frequency unit multiplier.

#### Safety-16: Sampling Uniqueness

Each peripheral may have at most one SAMPLING configuration:

$$\mathsf{Safety}_{\text{sample-unique}}(D) \Leftrightarrow \forall s_1, s_2 \in \mathit{samplings}(D) : s_1.\mathit{target} = s_2.\mathit{target} \Rightarrow s_1 = s_2$$

Duplicate SAMPLING blocks for the same peripheral are a semantic error.

#### Safety-17: On-Change Threshold Requirement

SAMPLING configurations with `on_change` mode must specify a positive threshold:

$$\mathsf{Safety}_{\text{threshold}}(D) \Leftrightarrow \forall s \in \mathit{samplings}(D) : s.\mathit{mode} = \mathsf{on\_change} \Rightarrow s.\mathit{threshold} > 0$$

Without a threshold, the on_change mode cannot determine when a value has changed significantly enough to publish.

#### Safety-18: Batch Buffer Requirement

SAMPLING configurations with `batch` mode must specify a positive buffer size:

$$\mathsf{Safety}_{\text{buffer}}(D) \Leftrightarrow \forall s \in \mathit{samplings}(D) : s.\mathit{mode} = \mathsf{batch} \Rightarrow s.\mathit{buffer} > 0$$

The buffer size determines how many samples to accumulate before publishing as a batch.

**Example:** `SAMPLING EnvSensor WITH rate = 10 hz, mode = on_change, threshold = 0.5;` is valid. Omitting `threshold` with `on_change` mode raises a semantic error.

### 8.9 Multi-Broker Safety

#### Safety-19: Broker Name Uniqueness

All declared brokers must have unique names:

$$\mathsf{Safety}_{\text{broker-unique}}(D) \Leftrightarrow \forall b_1, b_2 \in \mathit{brokers}(D) : b_1.\mathit{name} = b_2.\mathit{name} \Rightarrow b_1 = b_2$$

Duplicate broker names are a semantic error.

#### Safety-20: VIA Reference Resolution

All `VIA` references in connections must resolve to a declared broker:

$$\mathsf{Safety}_{\text{via-resolve}}(D) \Leftrightarrow \forall c \in \mathit{connections}(D) \cup \mathit{smartConnections}(D) : c.\mathit{via} \neq \bot \Rightarrow c.\mathit{via} \in \mathit{brokerNames}(D)$$

where $\mathit{brokerNames}(D) = \{b.\mathit{name} \mid b \in \mathit{brokers}(D)\}$.

**Example:** `CONNECT Sensor WITH ... VIA CloudBroker;` routes the connection's topic to the broker named `CloudBroker`. If no broker with that name exists, a semantic error is raised.

### 8.10 Alert Trigger Safety

#### Safety-21: Alert Name Uniqueness

$$\mathsf{Safety}_{\text{alert-unique}}(D) \Leftrightarrow \forall a_1, a_2 \in \mathit{alerts}(D) : a_1.\mathit{name} = a_2.\mathit{name} \Rightarrow a_1 = a_2$$

#### Safety-22: Alert Source Must Be Sensor

$$\mathsf{Safety}_{\text{alert-source}}(D) \Leftrightarrow \forall a \in \mathit{alerts}(D) : a.\mathit{source} \in \mathit{sensors}(D)$$

#### Safety-23: Alert ACTIVATE Target Must Be Actuator

$$\mathsf{Safety}_{\text{alert-target}}(D) \Leftrightarrow \forall a \in \mathit{alerts}(D), \forall act \in \mathit{activateActions}(a) : act.\mathit{target} \in \mathit{actuators}(D)$$

#### Safety-24: Alert VIA Resolution

$$\mathsf{Safety}_{\text{alert-via}}(D) \Leftrightarrow \forall a \in \mathit{alerts}(D), \forall pub \in \mathit{publishActions}(a) : pub.\mathit{via} \neq \bot \Rightarrow pub.\mathit{via} \in \mathit{brokerNames}(D)$$

#### Safety-25: Alert No Self-Activate

$$\mathsf{Safety}_{\text{alert-no-self}}(D) \Leftrightarrow \forall a \in \mathit{alerts}(D), \forall act \in \mathit{activateActions}(a) : act.\mathit{target} \neq a.\mathit{source}$$

### 8.11 Protocol Frequency Safety

#### Safety-26: I2C Bus Speed

$$\mathsf{Safety}_{\text{i2c-speed}}(D) \Leftrightarrow \forall c \in \mathit{connections}(D), \forall dc \in \mathit{dataConns}(c) : dc.\mathit{type} = \text{i2c} \wedge dc.\mathit{bus\_speed} \neq \bot \Rightarrow dc.\mathit{bus\_speed} \leq 3{,}400{,}000$$

Standard I2C modes: Standard (100 kHz), Fast (400 kHz), Fast Mode Plus (1 MHz), High Speed (3.4 MHz). Speeds above 400 kHz emit a warning; speeds above 3.4 MHz are errors.

#### Safety-27: SPI Bus Speed

$$\mathsf{Safety}_{\text{spi-speed}}(D) \Leftrightarrow \forall c \in \mathit{connections}(D), \forall dc \in \mathit{dataConns}(c) : dc.\mathit{type} = \text{spi} \wedge dc.\mathit{bus\_speed} \neq \bot \Rightarrow dc.\mathit{bus\_speed} \leq 80{,}000{,}000$$

---

## 9. Validation Algorithm

### 9.1 Algorithm Structure

The validation algorithm $\mathcal{V}$ takes a device model and produces either success or a set of errors:
$$\mathcal{V} : \mathit{Device} \to \mathbb{B} \times \mathcal{P}(\mathit{Error})$$

### 9.2 Validation Process

```
Algorithm: VALIDATE(D)
Input: Device model D
Output: (valid, errors)

1. errors ← ∅
2. Γ ← BUILD_ENVIRONMENT(D)

3. // Structural validation
4. if ¬WF_single-board(D) then
5.    errors ← errors ∪ {NO_BOARD_ERROR}
6. for each p ∈ peripherals do
7.    if ¬WF_unique-pins(p) then
8.       errors ← errors ∪ {DUPLICATE_PIN_ERROR(p)}

9. // SmartConnect structural validation
10. for each sc ∈ smartConnections do
11.    if target(sc) ∈ boards then
12.       errors ← errors ∪ {SC_TARGET_ERROR(sc)}
13.    if target(sc) ∈ targets(connections) then
14.       errors ← errors ∪ {SC_CONFLICT_ERROR(sc)}

15. // SmartConnect resolution
16. pool ← INIT_POOL(board, connections)
17. for each sc ∈ smartConnections (in declaration order) do
18.    (conn, pool) ← RESOLVE(sc, D, pool)
19.    if conn ≠ ⊥ then
20.       connections ← connections ∪ {conn}
21.    else
22.       errors ← errors ∪ {SC_RESOLUTION_ERROR(sc)}

23. // Referential integrity
10. for each c ∈ connections do
11.    if ¬RI_pins(c) then
12.       errors ← errors ∪ {INVALID_PIN_REF(c)}

13. // Connection validation
14. for each c ∈ connections do
15.    for each pc ∈ c.power_conns do
16.       if ¬valid_power(pc.src, pc.tgt) then
17.          errors ← errors ∪ {POWER_INCOMPATIBLE(pc)}
18.    for each dc ∈ c.data_conns do
19.       if ¬valid_data(dc.protocol, dc.mappings) then
20.          errors ← errors ∪ {DATA_INVALID(dc)}

21. // Safety properties
22. if ¬Safety_pin-conflicts(D) then
23.    errors ← errors ∪ {PIN_CONFLICT_ERROR}
24. if ¬Safety_i2c-unique(D) then
25.    errors ← errors ∪ {I2C_ADDRESS_CONFLICT}
26. if ¬Safety_power-path(D) then
27.    errors ← errors ∪ {NO_POWER_SOURCE}

28. // Power budget analysis (warnings)
29. if ¬Safety_power-budget(D) then
30.    warnings ← warnings ∪ {POWER_BUDGET_EXCEEDED}
31. for each ps ∈ power_sources do
32.    warnings ← warnings ∪ {BATTERY_RUNTIME(ps, D)}

33. // Pin function oversubscription (warnings)
34. for each c ∈ connections do
35.    for each bp ∈ usedBoardPins(c) do
36.       if ∃ f ∈ funcs(bp) : priority(f) > priority(usedAs(bp, c)) then
37.          warnings ← warnings ∪ {PIN_OVERSUBSCRIPTION(bp, c)}

 38. // User-defined constraint evaluation
 39. for each uc ∈ constraints do
 40.    result ← EVAL(uc.expr, D)
 41.    if result = ⊥ then
 42.       warnings ← warnings ∪ {CONSTRAINT_EVAL_ERROR(uc)}
 43.    else if result = false then
 44.       errors ← errors ∪ {CONSTRAINT_VIOLATED(uc)}

 45. // Multi-broker validation
 46. seen_broker_names ← ∅
 47. for each b ∈ brokers do
 48.    if b.name ∈ seen_broker_names then
 49.       errors ← errors ∪ {BROKER_DUPLICATE(b)}
 50.    seen_broker_names ← seen_broker_names ∪ {b.name}
 51. for each c ∈ connections ∪ smartConnections do
 52.    if c.via ≠ ⊥ ∧ c.via ∉ seen_broker_names then
 53.       errors ← errors ∪ {VIA_RESOLVE_ERROR(c)}

 54. // Sampling configuration validation
 46. seen_targets ← ∅
 47. for each s ∈ samplings do
 48.    if s.target ∈ seen_targets then
 49.       errors ← errors ∪ {SAMPLING_DUPLICATE(s)}
 50.    seen_targets ← seen_targets ∪ {s.target}
 51.    if s.target ∈ boards then
 52.       errors ← errors ∪ {SAMPLING_BOARD_TARGET(s)}
 53.    if toHz(s.rate, s.rate_unit) ≤ 0 then
 54.       errors ← errors ∪ {SAMPLING_RATE_ERROR(s)}
 55.    if s.mode = on_change ∧ (s.threshold = ⊥ ∨ s.threshold ≤ 0) then
 56.       errors ← errors ∪ {SAMPLING_THRESHOLD_ERROR(s)}
 57.    if s.mode = batch ∧ (s.buffer = ⊥ ∨ s.buffer ≤ 0) then
 58.       errors ← errors ∪ {SAMPLING_BUFFER_ERROR(s)}
 59.    if s.rate_hz > freq_max(s.target) then
 60.       warnings ← warnings ∪ {SAMPLING_RATE_WARNING(s)}

 61. // Protocol frequency validation
 62. for each c ∈ connections do
 63.    for each dc ∈ dataConns(c) do
 64.       if dc.type = i2c ∧ dc.bus_speed > 3,400,000 then
 65.          errors ← errors ∪ {I2C_SPEED_ERROR(dc)}
 66.       if dc.type = i2c ∧ dc.bus_speed > 400,000 then
 67.          warnings ← warnings ∪ {I2C_SPEED_WARNING(dc)}
 68.       if dc.type = spi ∧ dc.bus_speed > 80,000,000 then
 69.          errors ← errors ∪ {SPI_SPEED_ERROR(dc)}

 70. // Alert trigger validation
 71. seen_alert_names ← ∅
 72. for each a ∈ alerts do
 73.    if a.name ∈ seen_alert_names then
 74.       errors ← errors ∪ {ALERT_DUPLICATE(a)}
 75.    seen_alert_names ← seen_alert_names ∪ {a.name}
 76.    if a.source ∉ sensors then
 77.       errors ← errors ∪ {ALERT_SOURCE_ERROR(a)}
 78.    for each act ∈ activateActions(a) do
 79.       if act.target ∉ actuators then
 80.          errors ← errors ∪ {ALERT_TARGET_ERROR(act)}
 81.       if act.target = a.source then
 82.          errors ← errors ∪ {ALERT_SELF_ACTIVATE(a)}
 83.    for each pub ∈ publishActions(a) do
 84.       if pub.via ≠ ⊥ ∧ pub.via ∉ brokerNames then
 85.          errors ← errors ∪ {ALERT_VIA_ERROR(pub)}

 86. return (errors = ∅, errors)
```

### 9.3 Complexity Analysis

**Time Complexity:**
- Let $n = |peripherals|$, $m = |connections|$, $p = \max_c |\mathit{pins}(c)|$
- Building environment: $O(n \cdot p)$
- Pin conflict check: $O(m^2 \cdot p)$
- I2C uniqueness: $O(m^2)$
- Power path: $O(n \cdot m)$ (graph traversal)
- SmartConnect resolution: $O(|SC| \cdot p)$
- Sampling validation: $O(|S|)$ where $S$ = sampling configurations
- Alert validation: $O(|A| \cdot |actions|)$ where $A$ = alert triggers
- Protocol frequency: $O(m \cdot d)$ where $d$ = data connections per connection
- **Total:** $O(m^2 \cdot p + n \cdot m + |SC| \cdot p + |S| + |A|)$

**Space Complexity:** $O(n \cdot p + m)$

---

## 10. Formal Proofs

### 10.1 Soundness Theorem

**Theorem 1 (Soundness):** If $\mathcal{V}(D) = (\mathsf{true}, \emptyset)$, then $D$ represents a physically safe and electrically valid device configuration.

**Proof Sketch:**
1. By WF rules (WF-1 through WF-5), structural constraints hold
2. By WF-6/7/8, SmartConnect structural constraints hold
3. By Safety-1, no pin conflicts exist
4. By Safety-2, voltage limits respected
5. By Safety-7, all components powered
6. By §6.4 determinism, SmartConnect resolution is unique and produces valid connections
7. By Safety-8/9, resolved connections satisfy pin conflict freedom
8. By Safety-10, peripheral power demand does not exceed board supply (warning)
9. By Safety-12, multi-function pin usage is explicitly acknowledged (warning)
10. By Safety-13, all user-defined constraints are satisfied
11. By Safety-15/16/17/18, all sampling configurations are well-formed (positive rate, unique targets, mode-specific requirements)
12. By Safety-19/20, all broker names are unique and VIA references resolve
13. By Safety-21/22/23/24/25, all alert triggers are well-formed (unique names, sensor sources, actuator targets, VIA resolution, no self-activate)
14. By Safety-26/27, all I2C/SPI bus speeds are within standard limits
15. Therefore, $D$ is safe ∎

### 10.2 Decidability Theorem

**Theorem 2 (Decidability):** The validation algorithm $\mathcal{V}$ terminates for all inputs in finite time.

**Proof:**
1. All validation rules involve finite sets
2. No recursive definitions without base cases
3. Graph algorithms (e.g., reachability) terminate on finite graphs
4. Therefore, $\mathcal{V}$ always terminates ∎

### 10.3 Completeness Lemma

**Lemma 1 (Coverage):** Every safety violation is detected by at least one validation rule.

**Proof:** By case analysis on violation types:
- Pin conflicts → Safety-1
- Voltage incompatibility → PC-2, Safety-2
- Protocol errors → DC-1, Safety-5
- Missing power → Safety-7
- SmartConnect target errors → WF-6
- SmartConnect duplicate → WF-7
- SmartConnect-Connect conflict → WF-8
- SmartConnect pin allocation failure → Safety-8
- Power budget exceeded → Safety-10
- Battery runtime estimation → Safety-11
- Pin function oversubscription → Safety-12
- User-defined constraint violation → Safety-13
- Constraint evaluation failure → Safety-14
- Invalid sampling rate → Safety-15
- Duplicate sampling target → Safety-16
- Missing on_change threshold → Safety-17
- Missing batch buffer → Safety-18
- Duplicate broker name → Safety-19
- Unresolved VIA reference → Safety-20
- Duplicate alert name → Safety-21
- Alert source not a sensor → Safety-22
- Alert ACTIVATE target not an actuator → Safety-23
- Alert VIA unresolved → Safety-24
- Alert self-activate → Safety-25
- I2C bus speed exceeded → Safety-26
- SPI bus speed exceeded → Safety-27
∎

---

## Appendix A: Formal Grammar (BNF)

```bnf
<device> ::= "DEVICE" <id> "WITH" <metadata> <uses> <connections> <broker>* <network> <sampling>* <constraint>* <alert>*

<uses> ::= ( "USE" <component-ref> ";" )*

<component-ref> ::= <type> "[" <id> "]" ( "WITH" <attributes> )?

<connections> ::= ( <connect> | <smart-connect> )*

<connect> ::= "CONNECT" <conn-spec> ";"

<conn-spec> ::= (<id> ":")? <id> "WITH" <power-block>? <data-block>? ( "@" <string> )? <via>?

<via> ::= "VIA" <id>

<smart-connect> ::= "SMARTCONNECT" <id> ( "@" <string> )? <via>? ";"

<sampling> ::= "SAMPLING" <id> "WITH" <sampling-props> ";"

<sampling-props> ::= "rate" "=" <number> <freq-unit> ( "," "mode" "=" <sampling-mode> )?
                     ( "," "buffer" "=" <integer> )? ( "," "threshold" "=" <number> )?

<sampling-mode> ::= "continuous" | "on_change" | "on_demand" | "batch"

<freq-unit> ::= "ghz" | "mhz" | "khz" | "hz"

<constraint> ::= "CONSTRAINT" <id> ":" <constraint-expr> ( "MESSAGE" <string> )? ";"

<constraint-expr> ::= <additive-expr> <comp-op> <additive-expr>

<comp-op> ::= "<" | ">" | "<=" | ">=" | "==" | "!="

<additive-expr> ::= <mult-expr> ( ( "+" | "-" ) <mult-expr> )*

<mult-expr> ::= <atom-expr> ( ( "*" | "/" ) <atom-expr> )*

<atom-expr> ::= <func-call> | <prop-access> | <number> ( <unit> )? | <string> | <bool>

<func-call> ::= ( "count" | "sum_power" | "avg_power" | "max_power" ) "(" <func-arg> ")"

<func-arg> ::= "SENSOR" | "ACTUATOR" | "PERIPHERAL" | "CONNECTION"

<prop-access> ::= <id> ( "." <id> )+

<power-block> ::= "POWER" ( <pin-mapping> ( "," <pin-mapping> )* )

<data-block> ::= "DATA" ( <protocol-conn> ( "," <protocol-conn> )* )

<protocol-conn> ::= <protocol> ( "[" <properties> "]" )? <pin-mappings>

<pin-mapping> ::= <id> "--" <id>

<pwm-conn> ::= "pwm" ( "[" <properties> "]" )? <pin-mappings>

<alert> ::= "ALERT" <id> "ON" <id> "WHEN" <alert-condition> "THEN" <alert-action>+ ( "COOLDOWN" <number> <freq-unit> )? ";"

<alert-condition> ::= <alert-comparison> ( <logic-op> <alert-condition> )?

<alert-comparison> ::= <id> <comp-op> <number> ( <unit> )?

<logic-op> ::= "&&" | "||"

<alert-action> ::= <alert-publish> | <alert-activate>

<alert-publish> ::= "PUBLISH" <string> ( "VIA" <id> )?

<alert-activate> ::= "ACTIVATE" <id>
```

---

## Appendix B: Type Signatures

### Core Functions
```haskell
parseVoltage :: String → Maybe Voltage
compatible :: Voltage → Voltage → Bool
validPower :: Pin → Pin → Bool
validData :: Protocol → PinMapping → Bool
validate :: Device → (Bool, Set Error)
```

### Helper Functions
```haskell
usedPins :: Connection → Set Pin
sameBus :: Connection → Connection → Bool
reachable :: Component → Set Component → Set Connection → Bool
buildEnvironment :: Device → Environment
```

### Power Budget Functions
```haskell
toMW :: PowerConsumption → Float
peripheralSupplyBudget :: Board → Float
totalPeripheralPower :: Device → (Float, Float)  -- (max_mw, avg_mw)
batteryRuntime :: PowerSource → Float → Float     -- capacity, avg_power → hours
pinPriority :: PinFunction → Int
higherPriorityFunctions :: Pin → PinFunction → [PinFunction]
```

### Constraint Functions
```haskell
evalConstraint :: UserConstraint → Device → (Bool, Value, Value, Maybe Error)
evalAtom :: AtomExpr → Device → Value
evalBuiltinFunc :: String → String → Device → Float
getPeripheralsByKind :: Device → String → [ComponentInstance]
getAttributeValue :: ComponentInstance → String → Maybe Value
normalizeUnit :: Float → Maybe Unit → Float
```

### Sampling Functions
```haskell
toHz :: Float → FreqUnit → Float
validateSampling :: Device → [SamplingError]
checkDuplicateTargets :: [SamplingConfig] → Maybe SamplingError
checkSamplingRate :: SamplingConfig → Maybe SamplingError
checkOnChangeThreshold :: SamplingConfig → Maybe SamplingError
checkBatchBuffer :: SamplingConfig → Maybe SamplingError
```

### Multi-Broker Functions
```haskell
resolveBroker :: Connection → BrokerMap → Maybe Broker
buildBrokerMap :: [Broker] → Map String Broker
validateBrokerUniqueness :: [Broker] → Maybe BrokerError
validateVIAReferences :: [Connection] → Set String → [VIAError]
```

### Alert Functions
```haskell
validateAlerts :: Device → [AlertError]
checkAlertUniqueNames :: [AlertTrigger] → Maybe AlertError
checkAlertSource :: AlertTrigger → Set Sensor → Maybe AlertError
checkAlertTargets :: AlertTrigger → Set Actuator → Maybe AlertError
checkAlertVIA :: AlertTrigger → Set BrokerName → Maybe AlertError
walkCondition :: AlertConditionExpr → Maybe AlertError
```

### Protocol Frequency Functions
```haskell
classifyI2CSpeed :: Int → (String, Int)
validateI2CBusSpeed :: DataConnection → Maybe FrequencyError
validateSPIBusSpeed :: DataConnection → Maybe FrequencyError
validateProtocolFrequency :: Device → [FrequencyError]
```

### SmartConnect Functions
```haskell
resolveSmartConnect :: SmartConnDecl → Device → PinPool → (Connection, PinPool)
initPool :: Board → Set Connection → PinPool
classify :: Set Pin → Map Protocol (Set Pin)
primaryProto :: Pin → Protocol
inferMode :: Component → GPIOMode
findPowerPin :: PinPool → Voltage → Maybe Pin
findIOPin :: PinPool → PinFunction → Bus → Maybe Pin
findGPIOPin :: PinPool → Maybe Pin
```

---

## 11. Error Recovery and Reporting

### 11.1 Syntax Error Translation

The parser produces raw `TextXSyntaxError` exceptions that expose internal parser state (token names, arpeggio positions). The CLI translates these into domain-specific messages using pattern-matched hints:

$$\mathit{translate} : \mathit{SyntaxError} \to \mathit{DomainError}$$

| Raw Pattern | Domain Hint |
|-------------|-------------|
| `Expected ';'` | Missing semicolon at end of statement |
| `Expected 'WITH'` | Missing `WITH` keyword after declaration |
| `Expected 'DEVICE'` | Model must start with a `DEVICE` declaration |
| `Expected '--'` | Pin connections require `--` separator |
| `Expected ']'` | Unclosed bracket |
| `Expected 'THEN'` or `'WHEN'` | `ALERT` requires `WHEN ... THEN ...` syntax |
| `Expected 'description'` | `DEVICE` requires `description` and `author` attributes |

Each translated error includes:
- **Source location**: filename, line, column
- **Expected tokens**: in domain terms, not parser internals
- **Contextual hint**: actionable suggestion for the user

### 11.2 Parser Robustness Properties

The parser is verified against 57 robustness tests covering 15 categories of malformed input. The following properties are tested:

#### Property R-1: Graceful Rejection of Empty Input
$$\forall s \in \{\epsilon, \text{whitespace}, \text{comments-only}\} : \mathsf{parse}(s) = \mathit{SyntaxError}$$

The parser rejects empty, whitespace-only, and comment-only input with a syntax error rather than crashing.

#### Property R-2: Graceful Rejection of Truncated Input
$$\forall s \in \mathit{Prefix}(\mathit{ValidModel}) : |s| < |\mathit{ValidModel}| \Rightarrow \mathsf{parse}(s) \in \{\mathit{SyntaxError}, \mathit{Model}\}$$

Truncated input at any point (after `DEVICE`, after name, mid-block) produces a syntax error, not a crash or hang.

#### Property R-3: Boundary Value Tolerance
$$\forall n \in \{50\text{-char identifiers}, \text{long topics}, \text{empty strings}, \text{unicode}\} : \mathsf{parse}(\mathit{model}(n)) \neq \mathit{crash}$$

The parser handles boundary-length identifiers, very long MQTT topic strings, empty string attributes, and Unicode characters in string values.

#### Property R-4: Keyword Order Flexibility
The unordered group (`#` operator) in the grammar allows `SAMPLING`, `CONSTRAINT`, and `ALERT` blocks to appear in any order relative to `CONNECT` blocks within the device body.

#### Property R-5: Comment Immunity
$$\forall m \in \mathit{ValidModel}, c \in \mathit{Comments} : \mathsf{parse}(m \oplus c) = \mathsf{parse}(m)$$

Inline comments (`//`) and block comments (`/* */`) interspersed at any valid position do not affect parse results.

#### Known Limitation: `esp-idf-rtos` Grammar Ambiguity

The `OperatingSystem` rule declares `'esp-idf-rtos'` as a valid keyword, but the PEG parser greedily matches `'esp-idf'` first (the longer prefix match), leaving `-rtos` unparseable. This OS value is currently unreachable. Workaround: use `esp-idf` instead. This is tracked as a known grammar issue.

### 11.3 Performance Bounds

The parser and validation pipeline are benchmarked with regression thresholds to prevent performance degradation:

| Metric | Model Size | Threshold | Measured |
|--------|-----------|-----------|----------|
| Parse + skip-semantics | 1 peripheral | < 500 ms | ~200 ms |
| Parse + skip-semantics | 5 peripherals (SmartConnect) | < 1 s | ~400 ms |
| Parse + skip-semantics | 10 peripherals (mixed types) | < 3 s | ~1.5 s |
| Full validation pipeline | 1 peripheral | < 300 ms | ~200 ms |
| Metamodel construction | N/A (grammar loading) | < 1 s | ~300 ms |

These thresholds are enforced in the test suite (`test_performance.py`). CI failures indicate a performance regression.

The validation algorithm complexity from §9.3 is:
$$O(m^2 \cdot p + n \cdot m + |SC| \cdot p + |S| + |A|)$$

In practice, IoT device models have $n \leq 20$ peripherals and $m \leq 20$ connections, keeping validation well under 1 second.

---

## References

1. Pierce, B. C. (2002). *Types and Programming Languages*. MIT Press.
2. Winskel, G. (1993). *The Formal Semantics of Programming Languages*. MIT Press.
3. IEEE Standard for Hardware Description Languages (VHDL). IEEE Std 1076-2008.
4. MQTT Version 5.0. OASIS Standard, 2019.
5. AMQP Version 1.0. OASIS Standard, 2012.

---

**Document Version:** 3.6  
**Last Updated:** 2026-02-15  
**Status:** Formal Specification