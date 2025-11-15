using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("api/trivia")]
public class TriviaController : ControllerBase
{
    [HttpPost("generate")] // this makes POST /api/trivia/generate
    public IActionResult Generate([FromBody] TriviaRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.MonumentName) || 
            string.IsNullOrWhiteSpace(request.Description))
        {
            return BadRequest("Missing data.");
        }

        string trivia = $"Știați că {request.MonumentName} este {request.Description}?";

        return Ok(new { trivia });
    }
}

public class TriviaRequest
{
    public string MonumentName { get; set; }
    public string Description { get; set; }
}
