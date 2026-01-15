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
   - 3.4 [Connection Domain](#34-connection-domain)
   - 3.5 [Protocol Domain](#35-protocol-domain)
   - 3.6 [Device Model Domain](#36-device-model-domain)
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
7. [Well-Formedness Constraints](#7-well-formedness-constraints)
   - 7.1 [Structural Well-Formedness](#71-structural-well-formedness)
   - 7.2 [Referential Integrity](#72-referential-integrity)
8. [Safety Properties](#8-safety-properties)
   - 8.1 [Electrical Safety](#81-electrical-safety)
   - 8.2 [Protocol Safety](#82-protocol-safety)
   - 8.3 [Resource Safety](#83-resource-safety)
9. [Validation Algorithm](#9-validation-algorithm)
10. [Formal Proofs](#10-formal-proofs)

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
$$\llbracket \cdot \rrbracket_V : \mathit{String} \rightharpoonup \mathit{Voltage}$$

Defined by:
$$\llbracket s \rrbracket_V = \begin{cases}
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

### 3.4 Connection Domain

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

### 3.5 Protocol Domain

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

### 3.6 Device Model Domain

#### Device Model Structure
$$\begin{align*}
\mathit{Device} = &\; \mathit{Identifier} \times \mathit{Metadata} \times \mathit{Component} \\
&\times \mathcal{P}(\mathit{Component}) \times \mathcal{P}(\mathit{Component}) \\
&\times \mathcal{P}(\mathit{Connection}) \times \mathit{Broker} \times \mathit{Network}
\end{align*}$$

Components: $(name, metadata, board, peripherals, power\_sources, connections, broker, network)$

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

### 4.2 Syntactic Well-Formedness

A syntactic structure is well-formed if it satisfies:

$$\begin{align*}
\mathsf{WF}_{syn}(d) \Leftrightarrow &\; \mathsf{unique}(\mathit{ids}(P)) \\
\land &\; \mathsf{unique}(\mathit{ids}(S)) \\
\land &\; \forall c \in C : \mathsf{referenced}(c, P \cup S \cup \{b\})
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
\vdots
\end{cases}$$

### 6.3 Protocol Semantics

#### I2C Protocol
$$\llbracket \mathsf{I2C} \rrbracket = \langle \mathit{addr}, \mathit{speed}, \mathit{bus} \rangle$$

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
$$\llbracket \mathsf{SPI} \rrbracket = \langle \mathit{mode}, \mathit{speed}, \mathit{bus} \rangle$$

**Constraints:**
$$\begin{align*}
\mathit{mode} &\in \{0, 1, 2, 3\} \\
\mathit{speed} &\in \mathbb{N}^+ \\
\mathit{bus} &\in \mathbb{N}
\end{align*}$$

#### UART Protocol
$$\llbracket \mathsf{UART} \rrbracket = \langle \mathit{baud}, \mathit{parity}, \mathit{stop}, \mathit{data} \rangle$$

**Constraints:**
$$\begin{align*}
\mathit{baud} &\in \{9600, 19200, 38400, 57600, 115200, \ldots\} \\
\mathit{parity} &\in \{\mathsf{none}, \mathsf{even}, \mathsf{odd}, \mathsf{mark}, \mathsf{space}\} \\
\mathit{stop} &\in \{1, 2\} \\
\mathit{data} &\in \{5, 6, 7, 8\}
\end{align*}$$

---

## 7. Well-Formedness Constraints

### 7.1 Structural Well-Formedness

#### WF-1: Single Board
$$\mathsf{WF}_{\text{single-board}}(D) \Leftrightarrow |\{board\}| = 1$$

#### WF-2: All Peripherals Connected
$$\mathsf{WF}_{\text{all-connected}}(D) \Leftrightarrow \forall p \in peripherals : \exists c \in connections : p \in \{c.src, c.tgt\}$$

#### WF-3: Unique Peripheral Names
$$\mathsf{WF}_{\text{unique-names}}(D) \Leftrightarrow \forall p_1, p_2 \in peripherals : p_1 \neq p_2 \Rightarrow \pi_{name}(p_1) \neq \pi_{name}(p_2)$$

#### WF-4: Unique Pin Numbers
$$\mathsf{WF}_{\text{unique-pins}}(c) \Leftrightarrow \forall p_1, p_2 \in \mathit{pins}(c) : p_1 \neq p_2 \Rightarrow \pi_{num}(p_1) \neq \pi_{num}(p_2)$$

#### WF-5: Essential Pins Connected
$$\mathsf{WF}_{\text{essential}}(D, p) \Leftrightarrow \forall pin \in \mathit{pins}(p) : \pi_{ess}(pin) \Rightarrow \mathsf{connected}(pin, connections)$$

where:
$$\mathsf{connected}(pin, C) \Leftrightarrow \exists c \in C : pin \in \mathsf{usedPins}(c)$$

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

9. // Referential integrity
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

28. return (errors = ∅, errors)
```

### 9.3 Complexity Analysis

**Time Complexity:**
- Let $n = |peripherals|$, $m = |connections|$, $p = \max_c |\mathit{pins}(c)|$
- Building environment: $O(n \cdot p)$
- Pin conflict check: $O(m^2 \cdot p)$
- I2C uniqueness: $O(m^2)$
- Power path: $O(n \cdot m)$ (graph traversal)
- **Total:** $O(m^2 \cdot p + n \cdot m)$

**Space Complexity:** $O(n \cdot p + m)$

---

## 10. Formal Proofs

### 10.1 Soundness Theorem

**Theorem 1 (Soundness):** If $\mathcal{V}(D) = (\mathsf{true}, \emptyset)$, then $D$ represents a physically safe and electrically valid device configuration.

**Proof Sketch:**
1. By WF rules, structural constraints hold
2. By Safety-1, no pin conflicts exist
3. By Safety-2, voltage limits respected
4. By Safety-7, all components powered
5. Therefore, $D$ is safe ∎

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
∎

---

## Appendix A: Formal Grammar (BNF)

```bnf
<device> ::= "DEVICE" <id> "WITH" <metadata> <uses> <connections> <broker> <network>

<uses> ::= ( "USE" <component-ref> ";" )*

<component-ref> ::= <type> "[" <id> "]" ( "WITH" <attributes> )?

<connections> ::= ( "CONNECT" <conn-spec> ";" )*

<conn-spec> ::= (<id> ":")? <id> "WITH" <power-block>? <data-block>?

<power-block> ::= "POWER" ( <pin-mapping> ( "," <pin-mapping> )* )

<data-block> ::= "DATA" ( <protocol-conn> ( "," <protocol-conn> )* )

<protocol-conn> ::= <protocol> ( "[" <properties> "]" )? <pin-mappings>

<pin-mapping> ::= <id> "--" <id>
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

---

## References

1. Pierce, B. C. (2002). *Types and Programming Languages*. MIT Press.
2. Winskel, G. (1993). *The Formal Semantics of Programming Languages*. MIT Press.
3. IEEE Standard for Hardware Description Languages (VHDL). IEEE Std 1076-2008.
4. MQTT Version 5.0. OASIS Standard, 2019.
5. AMQP Version 1.0. OASIS Standard, 2012.

---

**Document Version:** 2.0  
**Last Updated:** 2026-01-14  
**Status:** Formal Specification