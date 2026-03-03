using UnityEngine;

public class OpenRocketRampLink : MonoBehaviour
{
    // You get this UUID from your own system (generate/store it per user on your side).
    // Example UUID:
    private const string PartnerUserId = "550e8400-e29b-41d4-a716-446655440000";

    public void OpenLink()
    {
        Debug.Log($"[Rocketramp] User clicked the Rocketramp button. Opened external login for partner_user_id={PartnerUserId}. " +
                  "Start polling your backend token endpoint now to retrieve the temporary access token after the user logs in.");

        Application.OpenURL($"https://test.rocket-ramp.com/?partner_user_id={PartnerUserId}");
    }
}