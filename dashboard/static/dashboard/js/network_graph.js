(function () {
    const dataElement = document.getElementById("network-graph-data");
    const svg = document.getElementById("network-graph");
    if (!dataElement || !svg) return;

    const data = JSON.parse(dataElement.textContent);
    const edgesGroup = document.getElementById("network-edges");
    const nodesGroup = document.getElementById("network-nodes");
    const inspector = document.getElementById("node-inspector-content");
    const nodesById = Object.fromEntries(data.nodes.map((node) => [node.id, node]));

    function selectNode(nodeId) {
        const node = nodesById[nodeId];
        document.querySelectorAll(".network-node").forEach((item) => item.classList.toggle("is-selected", item.dataset.nodeId === nodeId));
        document.querySelectorAll(".network-edge").forEach((edge) => edge.classList.toggle("is-selected", edge.dataset.source === nodeId || edge.dataset.target === nodeId));
        const incoming = data.edges.filter((edge) => edge.target === nodeId);
        const outgoing = data.edges.filter((edge) => edge.source === nodeId);
        const incomingAmount = incoming.reduce((sum, edge) => sum + Number(edge.amount), 0);
        const outgoingAmount = outgoing.reduce((sum, edge) => sum + Number(edge.amount), 0);
        inspector.innerHTML = "<strong>" + node.id + "</strong><p>" + node.role + "</p><dl><dt>Incoming transactions</dt><dd>" + incoming.reduce((sum, edge) => sum + edge.count, 0) + "</dd><dt>Outgoing transactions</dt><dd>" + outgoing.reduce((sum, edge) => sum + edge.count, 0) + "</dd><dt>Incoming amount</dt><dd>$" + incomingAmount.toFixed(2) + "</dd><dt>Outgoing amount</dt><dd>$" + outgoingAmount.toFixed(2) + "</dd><dt>Relationship</dt><dd>" + (node.kind === "focal" ? "Focal recipient" : "Connected to focal recipient") + "</dd></dl>";
    }

    data.edges.forEach((edge) => {
        const source = nodesById[edge.source];
        const target = nodesById[edge.target];
        const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
        line.setAttribute("x1", source.x); line.setAttribute("y1", source.y); line.setAttribute("x2", target.x); line.setAttribute("y2", target.y);
        line.setAttribute("stroke-width", edge.width); line.setAttribute("marker-end", "url(#network-arrow)");
        line.dataset.source = edge.source; line.dataset.target = edge.target; line.classList.add("network-edge");
        edgesGroup.appendChild(line);
    });
    data.nodes.forEach((node) => {
        const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
        const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
        circle.setAttribute("cx", node.x); circle.setAttribute("cy", node.y); circle.setAttribute("r", node.kind === "focal" ? 27 : 17);
        circle.classList.add("network-node", "node-" + node.kind); circle.dataset.nodeId = node.id; circle.setAttribute("tabindex", "0"); circle.setAttribute("role", "button"); circle.setAttribute("aria-label", node.id + ", " + node.role);
        const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
        label.setAttribute("x", node.x); label.setAttribute("y", node.y + (node.kind === "focal" ? 48 : 34)); label.textContent = node.label;
        label.classList.add("network-node-label");
        group.appendChild(circle); group.appendChild(label); nodesGroup.appendChild(group);
        circle.addEventListener("click", () => selectNode(node.id));
        circle.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectNode(node.id); } });
    });
    selectNode(data.nodes.find((node) => node.kind === "focal").id);
})();
