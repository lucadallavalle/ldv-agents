#!/usr/bin/env python3
"""Debug script to test HITL functionality in isolation."""
import asyncio
from pathlib import Path
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async def main():
    """Test HITL with a simple write_file request."""
    
    # Setup
    working_dir = Path("/tmp/hitl_test")
    working_dir.mkdir(exist_ok=True)
    
    sessions_db = working_dir / "sessions.db"
    
    print("Creating agent with HITL enabled...")
    
    async with AsyncSqliteSaver.from_conn_string(str(sessions_db)) as checkpointer:
        # Create agent with HITL
        agent = create_deep_agent(
            model="anthropic:claude-sonnet-4-5",
            backend=lambda rt: FilesystemBackend(root_dir=str(working_dir)),
            interrupt_on={
                "write_file": True,
                "edit_file": True,
            },
            checkpointer=checkpointer,
        )
        
        config = {
            "configurable": {
                "thread_id": "test_thread",
            }
        }
        
        # Try to trigger a write_file call
        print("\nSending request: 'Create a file called test.txt with hello world'")
        
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content="Create a file called test.txt with the text 'Hello World'")]},
            config=config
        )
        
        print(f"\nResult keys: {result.keys()}")
        
        if "__interrupt__" in result:
            print("\n✓ Interrupt detected!")
            interrupts = result["__interrupt__"]
            print(f"Number of interrupts: {len(interrupts)}")
            
            for i, interrupt_obj in enumerate(interrupts):
                print(f"\nInterrupt {i}:")
                print(f"  Keys: {interrupt_obj.keys()}")
                
                if "value" in interrupt_obj:
                    hitl_request = interrupt_obj["value"]
                    print(f"  HITL Request keys: {hitl_request.keys()}")
                    
                    if "action_requests" in hitl_request:
                        action_requests = hitl_request["action_requests"]
                        print(f"  Number of action requests: {len(action_requests)}")
                        
                        for j, action in enumerate(action_requests):
                            print(f"\n  Action {j}:")
                            print(f"    Name: {action.get('name')}")
                            print(f"    Args: {action.get('args')}")
            
            # Try to resume with approval
            print("\n\nAttempting to resume with approval...")
            decisions = [{"type": "approve"}]
            
            resume_result = await agent.ainvoke(
                Command(resume={"decisions": decisions}),
                config=config
            )
            
            print(f"\nResume result keys: {resume_result.keys()}")
            
            if "__interrupt__" in resume_result:
                print("⚠️  Still interrupted after resume!")
            else:
                print("✓ Execution completed after approval!")
                
                # Check if file was created
                test_file = working_dir / "test.txt"
                if test_file.exists():
                    print(f"✓ File created: {test_file.read_text()}")
                else:
                    print("✗ File was not created!")
        else:
            print("\n✗ No interrupt detected - HITL might not be working!")
            print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
