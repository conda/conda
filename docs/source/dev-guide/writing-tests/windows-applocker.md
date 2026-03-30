[AppLocker]: https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/applocker/applocker-overview
[Application Identity Service]: https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/applocker/configure-the-application-identity-service

# Testing with Windows AppLocker

Windows environments with [AppLocker][AppLocker] enabled present unique challenges for `conda` development and testing. This guide explains how to set up a testing environment with AppLocker to ensure `conda` works correctly in these environments.

## Why Test with AppLocker?

AppLocker is Microsoft's application control solution that allows organizations to:

- Control which applications and files users can run
- Create rules to allow or deny applications from running based on file attributes
- Create exceptions to rules

Many enterprise environments use AppLocker to restrict script execution, which can impact environmnet activation and execution processes. Testing with AppLocker ensures `conda` works properly in these restricted environments.

## Setting Up AppLocker for Testing


### Step 1: Enable the [Application Identity Service][Application Identity Service]

:::{note}
The Application Identity Service is required for AppLocker to function properly.
:::

1. Open the **Services** application (press `Win+R`, type `services.msc`, and press Enter)
2. Find **Application Identity** in the list of services
3. Right-click on it and select **Properties**
4. *Optional*: Change **Startup type** to **Automatic** if you want the service to start on boot
5. Click **Start** to start the service
6. Click **OK** to close the properties window

### Step 2: Configure AppLocker Enforcement

1. Open **Local Security Policy** (press `Win+R`, type `secpol.msc`, and press Enter)
2. Navigate to **Security Settings** > **Application Control Policies** > **AppLocker**
3. Right-click on **AppLocker** and select **Properties**
4. Under the **Enforcement** tab, check **Script Rules** and set it to **Enforce rules**
5. Click **OK** to close the properties window

### Step 3: Create AppLocker Rules

1. In the **Local Security Policy** window, navigate to **Script Rules** under **AppLocker**
2. Right-click on **Script Rules** and select **Create Default Rules** to establish baseline rules
3. Create an Allow Rule for your development environment:
   - Right-click on **Script Rules** and select **Create New Rule...**
   - Choose **Allow** under Permissions and set the user/group to **Everyone**
   - Select **Path** as the condition
   - Enter the path to your development environment (e.g., path to `devenv`)
   - Complete the wizard without adding exceptions
4. Create an Allow Rule for the conda source code location using the same process
5. Create a Deny Rule for the `%TEMP%` directory:
   - Follow the same process but choose **Deny** under Permissions
   - Set the absolute path
6. Restart your computer to apply the rules

```{figure} /img/applocker.png
   :name: Windows AppLocker

## Testing Conda with AppLocker Enabled

After setting up AppLocker, you can test conda to ensure it works correctly:

1. Start your development environment with `.\dev\start.bat`
2. Run `conda activate` to test activation
3. Test other conda commands to ensure they function properly

### Toggling AppLocker for Testing

You can easily toggle AppLocker enforcement on and off for quick testing:

1. Open **Local Security Policy** (press `Win+R`, type `secpol.msc`, and press Enter)
2. Navigate to **Security Settings** > **Application Control Policies** > **AppLocker**
3. Right-click on **AppLocker** and select **Properties**
4. Under the **Enforcement** tab, uncheck or check **Script Rules** as needed
5. Click **OK** to apply the changes

This allows you to quickly switch between testing with and without AppLocker restrictions without restarting your machine.
