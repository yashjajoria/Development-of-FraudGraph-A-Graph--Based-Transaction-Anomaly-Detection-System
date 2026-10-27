import { createSSEParser } from "./useCopilotStream";

describe("createSSEParser", () => {
  it("parses complete events", () => {
    const p = createSSEParser();
    const ev = p('event: session\ndata: {"session_id":"s1"}\n\nevent: token\ndata: {"text":"Hi"}\n\n');
    expect(ev).toEqual([{ event: "session", data: { session_id: "s1" } }, { event: "token", data: { text: "Hi" } }]);
  });
  it("buffers frames split across chunks", () => {
    const p = createSSEParser();
    expect(p('event: token\ndata: {"te')).toEqual([]);
    expect(p('xt":"₹5"}\n\n')).toEqual([{ event: "token", data: { text: "₹5" } }]);
  });
  it("skips malformed frames and handles CRLF", () => {
    const p = createSSEParser();
    const ev = p('event: token\r\ndata: {bad\r\n\r\nevent: done\r\ndata: {"message_id":"m"}\r\n\r\n');
    expect(ev).toEqual([{ event: "done", data: { message_id: "m" } }]);
  });
});
