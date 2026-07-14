"use strict";

export class VideoConnection {
    constructor(
        videoElement,
        offerUrl,
        {
            onStateChange = null,
            reconnectDelayMs = 2000,
        } = {}
    ) {
        this.videoElement = videoElement;
        this.offerUrl = offerUrl;
        this.onStateChange = onStateChange;
        this.reconnectDelayMs =
            reconnectDelayMs;

        this.peerConnection = null;
        this.reconnectTimer = null;
        this.closed = false;
        this.connecting = false;
    }

    setState(state) {
        if (
            typeof this.onStateChange ===
            "function"
        ) {
            this.onStateChange(state);
        }
    }

    async connect() {
        if (
            this.closed ||
            this.connecting
        ) {
            return;
        }

        this.connecting = true;
        this.clearReconnect();

        try {
            await this.closePeer();

            this.setState("connecting");

            const peerConnection =
                new RTCPeerConnection();

            this.peerConnection =
                peerConnection;

            peerConnection.ontrack =
                (event) => {
                    const stream =
                        event.streams[0];

                    if (stream) {
                        this.videoElement
                            .srcObject = stream;

                        this.setState(
                            "connected"
                        );
                    }
                };

            peerConnection
                .onconnectionstatechange =
                () => {
                    const state =
                        peerConnection
                            .connectionState;

                    if (
                        state ===
                        "connected"
                    ) {
                        this.setState(
                            "connected"
                        );

                        return;
                    }

                    if (
                        state === "failed" ||
                        state ===
                            "disconnected" ||
                        state === "closed"
                    ) {
                        this.setState(
                            "disconnected"
                        );

                        this.scheduleReconnect();
                    }
                };

            peerConnection.addTransceiver(
                "video",
                {
                    direction: "recvonly",
                }
            );

            const offer =
                await peerConnection
                    .createOffer();

            await peerConnection
                .setLocalDescription(
                    offer
                );

            const response = await fetch(
                this.offerUrl,
                {
                    method: "POST",
                    cache: "no-store",
                    headers: {
                        "Content-Type":
                            "application/json",
                        Accept:
                            "application/json",
                    },
                    body: JSON.stringify({
                        sdp:
                            peerConnection
                                .localDescription
                                .sdp,

                        type:
                            peerConnection
                                .localDescription
                                .type,
                    }),
                }
            );

            if (!response.ok) {
                const details =
                    await response.text();

                throw new Error(
                    `Vision offer failed: `
                    + `${response.status} `
                    + details
                );
            }

            const answer =
                await response.json();

            await peerConnection
                .setRemoteDescription(
                    answer
                );

        } catch (error) {
            console.error(
                "WebRTC connection failed",
                error
            );

            this.setState("error");
            this.scheduleReconnect();

        } finally {
            this.connecting = false;
        }
    }

    scheduleReconnect() {
        if (
            this.closed ||
            this.reconnectTimer !== null
        ) {
            return;
        }

        this.reconnectTimer =
            window.setTimeout(
                () => {
                    this.reconnectTimer =
                        null;

                    this.connect();
                },
                this.reconnectDelayMs
            );
    }

    clearReconnect() {
        if (
            this.reconnectTimer === null
        ) {
            return;
        }

        window.clearTimeout(
            this.reconnectTimer
        );

        this.reconnectTimer = null;
    }

    async closePeer() {
        const peerConnection =
            this.peerConnection;

        this.peerConnection = null;

        if (peerConnection !== null) {
            peerConnection
                .ontrack = null;

            peerConnection
                .onconnectionstatechange =
                null;

            peerConnection.close();
        }

        this.videoElement.srcObject =
            null;
    }

    async close() {
        this.closed = true;
        this.clearReconnect();
        await this.closePeer();
        this.setState("closed");
    }
}
